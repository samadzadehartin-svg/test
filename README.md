# safaroiranian — Complete V1 + Video Hero

نسخه کامل اولیه بازطراحی سایت safaroiranian با رابط RTL دارک و لوکس و بک‌گراند ویدیویی Hero.

## Stack
- Frontend: Next.js 16 + React 19
- Backend: Node.js + NestJS 11
- CSS/UI: Tailwind CSS 4 + DaisyUI 5

## اجرا
### Backend
```bash
cd backend
npm install
npm run start:dev
```
API روی `http://localhost:4000/api` اجرا می‌شود.

### Frontend
در یک ترمینال دیگر:
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```
سایت روی `http://localhost:3000` اجرا می‌شود.

## APIهای فعلی
- `GET /api/health`
- `GET /api/destinations`
- `GET /api/tours`
- `GET /api/tours?destination=استانبول`

## قدم‌های بعدی پیشنهادی
- PostgreSQL + Prisma یا TypeORM
- احراز هویت و پنل مدیریت
- CRUD تور، هتل، پرواز، مقصد و مقاله
- موتور جستجو و فیلتر واقعی
- فرم لید و اتصال به CRM
- رزرو/پرداخت
- SEO صفحات مقصد و تور


## ویدیوی Hero
فایل‌های ویدیو داخل پروژه قرار دارند و نیازی به لینک خارجی ندارند:
- `frontend/public/videos/hero-istanbul.mp4`
- `frontend/public/videos/hero-istanbul-poster.jpg`

ویدیو به‌صورت `autoplay + muted + loop + playsInline` اجرا می‌شود و یک لایه تیره برای خوانایی متن روی آن قرار گرفته است. برای کاربرانی که Reduce Motion را فعال کرده‌اند، تصویر Poster نمایش داده می‌شود.


تغییرات نسخه به‌روزشده:
- نام نمایشی برند در رابط کاربری به «سفروایرانیان» و شناسه/نام پروژه به `safaroiranian` تنظیم شد.
- فیلد تاریخ به صورت شمسی (سال/ماه/روز) پیاده‌سازی شد.
- Hero از ویدیو MP4 داخلی پروژه استفاده می‌کند و فقط برای حالت کاهش حرکت از پوستر استفاده می‌شود.

- ویدئو اکنون پس‌زمینه ثابت تمام صفحه است و با اسکرول افکت پارالاکس/زوم ملایم می‌گیرد.
