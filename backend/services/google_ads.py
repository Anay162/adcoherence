"""
Google Ads API client.

Wraps the google-ads Python library with async-friendly helpers.
All heavy API calls are run in a thread pool executor to avoid blocking
the FastAPI event loop.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any
import logging

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

logger = logging.getLogger(__name__)

# GAQL query to pull all enabled RSAs + final URLs
ADS_QUERY = """
SELECT
    campaign.id,
    campaign.name,
    ad_group.id,
    ad_group.name,
    ad_group_ad.ad.id,
    ad_group_ad.ad.responsive_search_ad.headlines,
    ad_group_ad.ad.responsive_search_ad.descriptions,
    ad_group_ad.ad.final_urls,
    ad_group_ad.status
FROM ad_group_ad
WHERE ad_group_ad.status = 'ENABLED'
    AND campaign.status = 'ENABLED'
    AND ad_group.status = 'ENABLED'
    AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
"""

# GAQL query to pull keyword-level QS + 30-day metrics
KEYWORDS_QUERY = """
SELECT
    campaign.id,
    ad_group.id,
    ad_group.name,
    ad_group_criterion.criterion_id,
    ad_group_criterion.keyword.text,
    ad_group_criterion.keyword.match_type,
    ad_group_criterion.quality_info.quality_score,
    ad_group_criterion.quality_info.landing_page_experience,
    ad_group_criterion.quality_info.expected_ctr,
    ad_group_criterion.quality_info.ad_relevance,
    metrics.average_cpc,
    metrics.clicks,
    metrics.cost_micros,
    metrics.conversions
FROM keyword_view
WHERE segments.date DURING LAST_30_DAYS
    AND ad_group_criterion.status = 'ENABLED'
    AND campaign.status = 'ENABLED'
    AND ad_group.status = 'ENABLED'
"""


def _build_client(developer_token: str, client_id: str, client_secret: str, refresh_token: str) -> GoogleAdsClient:
    """Build a GoogleAdsClient from OAuth credentials (no yaml file needed)."""
    config = {
        "developer_token": developer_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "use_proto_plus": True,
    }
    return GoogleAdsClient.load_from_dict(config)


def _list_accessible_customers_sync(client: GoogleAdsClient) -> list[dict]:
    """Synchronous helper — returns list of {customer_id, descriptive_name}."""
    customer_service = client.get_service("CustomerService")
    response = customer_service.list_accessible_customers()
    results = []
    for resource_name in response.resource_names:
        # resource_name looks like "customers/1234567890"
        cid = resource_name.split("/")[-1]
        # Format as XXX-XXX-XXXX for display
        formatted = f"{cid[:3]}-{cid[3:6]}-{cid[6:]}" if len(cid) == 10 else cid
        results.append({"customer_id": cid, "formatted_id": formatted, "account_name": formatted})
    return results


def _fetch_account_name_sync(client: GoogleAdsClient, customer_id: str) -> str:
    """Fetch the descriptive name for a customer account."""
    ga_service = client.get_service("GoogleAdsService")
    query = "SELECT customer.descriptive_name FROM customer LIMIT 1"
    try:
        stream = ga_service.search_stream(customer_id=customer_id, query=query)
        for batch in stream:
            for row in batch.results:
                return row.customer.descriptive_name
    except GoogleAdsException:
        pass
    return customer_id


def _fetch_ads_sync(client: GoogleAdsClient, customer_id: str) -> list[dict]:
    """Synchronous: pull all enabled RSAs for the account."""
    ga_service = client.get_service("GoogleAdsService")
    stream = ga_service.search_stream(customer_id=customer_id, query=ADS_QUERY)

    ads = []
    for batch in stream:
        for row in batch.results:
            ad = row.ad_group_ad.ad
            rsa = ad.responsive_search_ad

            headlines = [asset.text.text for asset in rsa.headlines if asset.text.text]
            descriptions = [asset.text.text for asset in rsa.descriptions if asset.text.text]
            final_urls = list(ad.final_urls)

            if not final_urls:
                continue  # Skip ads with no destination URL

            ads.append({
                "campaign_id": str(row.campaign.id),
                "campaign_name": row.campaign.name,
                "ad_group_id": str(row.ad_group.id),
                "ad_group_name": row.ad_group.name,
                "ad_id": str(ad.id),
                "ad_headlines": headlines,
                "ad_descriptions": descriptions,
                "final_url": final_urls[0],  # Primary URL
            })

    return ads


def _fetch_keywords_sync(client: GoogleAdsClient, customer_id: str) -> dict[str, list[dict]]:
    """
    Synchronous: pull keyword QS + metrics, grouped by ad_group_id.
    Returns {ad_group_id: [keyword_dict, ...]}
    """
    ga_service = client.get_service("GoogleAdsService")
    stream = ga_service.search_stream(customer_id=customer_id, query=KEYWORDS_QUERY)

    # Enum display value helpers
    lpe_enum = client.enums.QualityScoreEnum  # Not used directly; we map string values
    match_type_enum = client.enums.KeywordMatchTypeEnum

    by_ad_group: dict[str, list[dict]] = {}

    for batch in stream:
        for row in batch.results:
            criterion = row.ad_group_criterion
            metrics = row.metrics
            qi = criterion.quality_info

            # Google returns enum int values; convert to string names
            lpe_str = _enum_name(
                qi.landing_page_experience,
                {0: "UNSPECIFIED", 1: "UNKNOWN", 2: "ABOVE_AVERAGE", 3: "AVERAGE", 4: "BELOW_AVERAGE"},
            )
            expected_ctr_str = _enum_name(
                qi.expected_ctr,
                {0: "UNSPECIFIED", 1: "UNKNOWN", 2: "ABOVE_AVERAGE", 3: "AVERAGE", 4: "BELOW_AVERAGE"},
            )
            ad_relevance_str = _enum_name(
                qi.ad_relevance,
                {0: "UNSPECIFIED", 1: "UNKNOWN", 2: "ABOVE_AVERAGE", 3: "AVERAGE", 4: "BELOW_AVERAGE"},
            )
            match_type_str = _enum_name(
                criterion.keyword.match_type,
                {0: "UNSPECIFIED", 1: "UNKNOWN", 2: "EXACT", 3: "PHRASE", 4: "BROAD"},
            )

            kw = {
                "keyword_text": criterion.keyword.text,
                "match_type": match_type_str,
                "quality_score": qi.quality_score if qi.quality_score else None,
                "landing_page_experience": lpe_str,
                "expected_ctr": expected_ctr_str,
                "ad_relevance": ad_relevance_str,
                "avg_cpc_micros": metrics.average_cpc,
                "clicks_30d": metrics.clicks,
                "cost_micros_30d": metrics.cost_micros,
                "conversions_30d": metrics.conversions,
            }

            ag_id = str(row.ad_group.id)
            by_ad_group.setdefault(ag_id, []).append(kw)

    return by_ad_group


def _enum_name(value: int, mapping: dict) -> str:
    return mapping.get(value, "UNKNOWN")


class GoogleAdsService:
    """Async-friendly wrapper around the Google Ads client library."""

    def __init__(
        self,
        developer_token: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ):
        self._developer_token = developer_token
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._executor = ThreadPoolExecutor(max_workers=4)

    def _get_client(self) -> GoogleAdsClient:
        return _build_client(
            self._developer_token,
            self._client_id,
            self._client_secret,
            self._refresh_token,
        )

    async def _run_sync(self, fn, *args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, fn, *args)

    async def list_accessible_customers(self) -> list[dict]:
        """List all Google Ads accounts the OAuth user can access."""
        client = self._get_client()
        accounts = await self._run_sync(_list_accessible_customers_sync, client)

        # Enrich with account names (one extra API call per account)
        async def enrich(acc: dict) -> dict:
            name = await self._run_sync(_fetch_account_name_sync, client, acc["customer_id"])
            acc["account_name"] = name or acc["formatted_id"]
            return acc

        enriched = await asyncio.gather(*[enrich(a) for a in accounts])
        return list(enriched)

    async def fetch_all_ad_data(self, customer_id: str) -> list[dict]:
        """
        Pull all enabled RSAs + keyword data for an account.
        Returns a list of ad dicts, each with a 'keywords' key containing
        the keywords for that ad's ad group.
        """
        client = self._get_client()

        # Fetch ads and keywords in parallel
        ads, keywords_by_ag = await asyncio.gather(
            self._run_sync(_fetch_ads_sync, client, customer_id),
            self._run_sync(_fetch_keywords_sync, client, customer_id),
        )

        # Attach keywords to each ad by ad_group_id
        for ad in ads:
            ad["keywords"] = keywords_by_ag.get(ad["ad_group_id"], [])

        logger.info(
            "Fetched %d ads across %d ad groups for account %s",
            len(ads),
            len(keywords_by_ag),
            customer_id,
        )
        return ads
