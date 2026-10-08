import "./globals.css";

export const metadata = { title: "FlowMap", description: "See how any project flows" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
