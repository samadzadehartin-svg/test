import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "safaroiranian | تورهای خاص، تجربه‌های ماندگار",
  description: "جستجو، مقایسه و رزرو تورهای خارجی و داخلی با safaroiranian",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fa" dir="rtl" data-theme="night">
      <body>{children}</body>
    </html>
  );
}
