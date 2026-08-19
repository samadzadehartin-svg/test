import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SafaroIranian | رزرو تور",
  description: "انتخاب سریع تور با فیلتر قاره، نوع سفر و بودجه",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fa" dir="rtl" data-theme="light">
      <body>{children}</body>
    </html>
  );
}
