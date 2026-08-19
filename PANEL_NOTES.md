# SafaroIranian Staff Panels

## هدف UX
پنل مدیر و کارشناس عمداً از یک UI شلوغ CRM تقلید نمی‌کنند. اطلاعات عملیاتی در اولویت هستند: صف درخواست، مالک پرونده، وضعیت فروش، یادداشت و اقدام بعدی.

## Admin
- Dashboard: KPI، قیف فروش، درخواست‌های اخیر و بار کاری تیم
- Leads: تغییر status، assignment و note داخل هر ردیف با `<details>` بدون JavaScript سمت کاربر
- Tours: price/tag/publish از یک صفحه
- Team: workload و close rate

## Expert
- Today: پرونده‌های شخصی + صف آزاد
- Leads: Claim درخواست و پیگیری وضعیت/یادداشت

## Performance
هیچ chart library، grid library، animation library، icon package یا client-side state manager اضافه نشده است. نمودار قیف با CSS ساده ساخته شده و mutationها Server Action هستند.

## Production checklist
1. PostgreSQL برای tours/leads/staff
2. Redis یا DB-backed sessions
3. Password hashing و مدیریت کاربران واقعی
4. Audit log برای تغییر وضعیت/قیمت/assignment
5. Rate limiting روی login و lead endpoints
6. CRM/telephony integration در صورت نیاز
