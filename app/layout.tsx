import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {
  title: 'Drug Discovery RSS · Research and tools',
  description: 'A compact research feed for drug discovery, cheminformatics, biologics, and open-source tools. Public sources, refreshed throughout the day.',
};
export default function RootLayout({ children }: Readonly<{children: React.ReactNode}>) {
  return <html lang="en"><body>{children}</body></html>;
}
