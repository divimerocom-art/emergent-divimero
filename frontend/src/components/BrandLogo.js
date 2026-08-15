import { Link } from "react-router-dom";

/**
 * The brand lockup: the Divimero mark plus the wordmark, always linking to "/".
 *
 * The mark is a transparent PNG served from /public, sized in CSS but carrying
 * explicit width/height so the browser reserves the box before the image
 * decodes — no layout shift on first paint.
 *
 * Accessibility: the visible wordmark "divimero" sits immediately beside the
 * image, so the image itself is decorative (alt="") — giving it alt="Divimero"
 * would make a screen reader announce the brand twice. The meaningful name goes
 * on the link, where it can also state the destination.
 */
export default function BrandLogo({ size = "md", testId }) {
  const box = size === "sm" ? "h-8 w-8" : "h-9 w-9";
  const text = size === "sm" ? "text-lg" : "text-xl";
  return (
    <Link
      to="/"
      aria-label="Divimero — ana sayfa"
      data-testid={testId}
      className="flex items-center gap-2 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2"
    >
      <img
        src="/logo.png"
        alt=""
        width="144"
        height="144"
        decoding="async"
        className={`${box} object-contain shrink-0`}
      />
      <span className={`font-heading font-bold ${text} tracking-tight`}>divimero</span>
    </Link>
  );
}
