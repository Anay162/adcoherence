import Link from "next/link";

export default function LandingPage() {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  return (
    <main className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="border-b border-gray-100 px-6 py-4 flex items-center justify-between max-w-6xl mx-auto">
        <span className="font-bold text-xl text-gray-900">AdCoherence</span>
        <a
          href={`${backendUrl}/auth/google/login`}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          Connect Google Ads — Free
        </a>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-20 pb-16 text-center">
        <div className="inline-block bg-red-50 text-red-700 text-sm font-medium px-3 py-1 rounded-full mb-6">
          Free audit — no credit card required
        </div>
        <h1 className="text-5xl font-bold text-gray-900 mb-6 leading-tight">
          Your ads are sending people to<br />
          <span className="text-red-600">the wrong landing pages.</span>
        </h1>
        <p className="text-xl text-gray-600 mb-10 max-w-2xl mx-auto">
          AdCoherence audits every active Google Ad against its landing page,
          scores the message match, and shows you exactly how much you're wasting
          — and how to fix it.
        </p>
        <a
          href={`${backendUrl}/auth/google/login`}
          className="inline-flex items-center gap-3 bg-blue-600 text-white px-8 py-4 rounded-xl text-lg font-semibold hover:bg-blue-700 transition-colors shadow-lg"
        >
          <GoogleIcon />
          Connect Google Ads Account
        </a>
        <p className="text-sm text-gray-400 mt-4">
          Read-only access. We never modify your campaigns.
        </p>
      </section>

      {/* Social proof numbers */}
      <section className="bg-gray-50 py-12">
        <div className="max-w-4xl mx-auto px-6 grid grid-cols-3 gap-8 text-center">
          <Stat value="47%" label="Average coherence score we find" />
          <Stat value="$1,240" label="Average monthly waste discovered" />
          <Stat value="2 min" label="Time to complete your first audit" />
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">How it works</h2>
        <div className="grid grid-cols-3 gap-8">
          <Step n={1} title="Connect your account" desc="Sign in with Google and grant read-only access to your Google Ads account. Takes 30 seconds." />
          <Step n={2} title="We audit everything" desc="AdCoherence pulls every active ad, scrapes each landing page, and scores them with AI." />
          <Step n={3} title="Fix the worst offenders" desc="See ranked mismatches, plain-English diagnoses, and specific recommendations for each ad." />
        </div>
      </section>

      {/* What we score */}
      <section className="bg-gray-50 py-16">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-8 text-center">What we score</h2>
          <div className="grid grid-cols-2 gap-4">
            {[
              { title: "Headline Match (30%)", desc: "Does your H1 reflect what the ad promised?" },
              { title: "Offer Consistency (25%)", desc: "Is your ad's discount/trial visible above the fold?" },
              { title: "CTA Alignment (20%)", desc: "Does your page CTA continue the ad's call to action?" },
              { title: "Keyword Relevance (15%)", desc: "Are target keywords in the page content? Affects Quality Score." },
              { title: "Tone Continuity (10%)", desc: "Does the page tone match the ad's voice?" },
              { title: "Quality Score data", desc: "We pull your actual Google QS + landing page experience scores." },
            ].map((item) => (
              <div key={item.title} className="bg-white rounded-lg p-4 border border-gray-200">
                <div className="font-semibold text-gray-900 text-sm mb-1">{item.title}</div>
                <div className="text-gray-500 text-sm">{item.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-4xl mx-auto px-6 py-20 text-center">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">Ready to stop wasting ad spend?</h2>
        <p className="text-gray-600 mb-8">Free audit. No credit card. Takes 2 minutes.</p>
        <a
          href={`${backendUrl}/auth/google/login`}
          className="inline-flex items-center gap-3 bg-blue-600 text-white px-8 py-4 rounded-xl text-lg font-semibold hover:bg-blue-700 transition-colors shadow-lg"
        >
          <GoogleIcon />
          Get My Free Audit
        </a>
      </section>

      <footer className="border-t border-gray-100 py-8 text-center text-sm text-gray-400">
        AdCoherence — Read-only Google Ads access. Your data is never shared or sold.
      </footer>
    </main>
  );
}

function GoogleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <div className="text-3xl font-bold text-gray-900">{value}</div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </div>
  );
}

function Step({ n, title, desc }: { n: number; title: string; desc: string }) {
  return (
    <div>
      <div className="w-8 h-8 rounded-full bg-blue-600 text-white text-sm font-bold flex items-center justify-center mb-4">{n}</div>
      <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-500 text-sm">{desc}</p>
    </div>
  );
}
