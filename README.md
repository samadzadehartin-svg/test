# SafaroIranian — Next.js + NestJS

نسخه سبک و Server-First سایت تور.

## معماری
- Frontend: Next.js App Router
- Backend: Node.js + NestJS
- CSS/UI: Tailwind CSS + daisyUI
- JavaScript سمت کاربر: حداقلی؛ صفحه اصلی و مسیر رزرو Client Component ندارند.
- فیلترها با Query String و رندر سمت سرور کار می‌کنند.
- بدون Framer Motion، Swiper، jQuery، icon pack و state manager.
- UI کارت‌ها با CSS سبک ساخته شده و برای ظاهر اصلی به تصویر یا اسلایدر سنگین وابسته نیست.

## اجرا

```bash
npm install
cp .env.example apps/web/.env.local
cp .env.example apps/api/.env
```

ترمینال ۱:
```bash
npm run dev:api
```

ترمینال ۲:
```bash
npm run dev:web
```

Frontend:
`http://localhost:3000`

API:
`http://localhost:4000/api`

## API
- `GET /api/tours`
- `GET /api/tours/:id`
- `POST /api/leads`
- `GET /api/health`

### فیلتر تور
مثال:
`/api/tours?continent=asia&tripType=international&budget=mid`

## نکته تولید
فعلاً Leadها در حافظه نگهداری می‌شوند. برای نسخه واقعی، `LeadsService` را به CRM/Database وصل کنید.


## پنل مدیریت و کارشناس

ورود کارکنان: `http://localhost:3000/staff/login`

حساب‌های دموی توسعه (در production حتماً از `.env` تغییر دهید):

- مدیر: `admin / admin123`
- کارشناس: `expert / expert123`

### پنل مدیر
- `/admin` داشبورد فروش
- `/admin/leads` مدیریت درخواست‌ها، تخصیص کارشناس، وضعیت و یادداشت
- `/admin/tours` مدیریت قیمت، برچسب و انتشار تور
- `/admin/team` عملکرد و بار کاری کارشناسان

### پنل کارشناس
- `/expert` کارهای امروز و صف آزاد
- `/expert/leads` پرونده‌های اختصاصی، Claim درخواست جدید، وضعیت و یادداشت

### معماری سبک پنل
- بدون کتابخانه Chart، Data Grid، Icon Pack یا State Manager
- احراز هویت با session در حافظه NestJS و HttpOnly cookie در Next.js
- فرم‌ها با Server Actions؛ صفحات پنل Server Component باقی مانده‌اند
- داده‌های Lead و Session فعلاً In-Memory هستند. برای production باید PostgreSQL/Redis یا سرویس‌های معادل متصل شوند.
