# Safar Iranian — V1

نسخه اولیه بازطراحی سایت سفر ایرانیان با رابط RTL دارک و لوکس.

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
