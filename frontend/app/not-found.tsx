import Link from "next/link";

export default function NotFound() {
  return (
    <div className="panel mx-auto mt-16 max-w-lg p-10 text-center">
      <p className="font-mono text-4xl font-semibold text-slate-700">404</p>
      <h1 className="mt-3 text-lg font-semibold text-white">
        Nothing registered here
      </h1>
      <p className="mt-2 text-sm text-slate-400">
        That page doesn&apos;t exist. The model may have been removed, or the
        link may be wrong.
      </p>
      <Link href="/" className="btn-primary mt-6">
        Back to the portfolio
      </Link>
    </div>
  );
}
