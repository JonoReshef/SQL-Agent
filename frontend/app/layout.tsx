import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Westbrand Product & Inventory Chat',
  description:
    'Natural language interface to Westbrand product and inventory data',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang='en'>
      <body>{children}</body>
    </html>
  );
}
