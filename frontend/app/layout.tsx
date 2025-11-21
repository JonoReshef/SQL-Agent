import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'WestBrand SQL Chat',
  description: 'Natural language interface to WestBrand database',
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
