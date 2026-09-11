/* eslint-disable react-refresh/only-export-components */
import '../src/index.css';

export const metadata = {
  title: 'Stream Analytics',
  description: 'Real-time stream analytics dashboard',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
