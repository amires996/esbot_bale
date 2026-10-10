# راهنمای نصب ESBot (نسخه توسعه‌ای)

> این بسته نسخه اولیه و ناقص پروژه است؛ هنوز برای بهره‌برداری واقعی شرکت آماده نیست. موارد ناقص در `KNOWN_ISSUES.md` آمده‌اند.

## پیش‌نیازها
- Python نسخه ۳.۱۲ یا جدیدتر
- Node.js نسخه ۲۰ یا جدیدتر و npm
- برای تولید: PostgreSQL؛ SQLite فقط برای توسعه محلی

## نصب بک‌اند
1. فایل `.env.example` را به `.env` کپی کنید.
2. مقدار `SECRET_KEY` را با یک راز تصادفی حداقل ۳۲ کاراکتری جایگزین کنید.
3. در پوشه `backend` محیط مجازی بسازید:

   **Windows PowerShell**
   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e ".[test]"
   ```

   **Linux/macOS**
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -e '.[test]'
   ```
4. مدیر اولیه را از ترمینال مورد اعتماد بسازید: `python ../scripts/create_admin.py`
5. سرور توسعه را اجرا کنید: `uvicorn app.main:app --reload`

## نصب فرانت‌اند
در ترمینال جداگانه:
```bash
cd frontend
npm install
npm run dev
```
رابط در نشانی نمایش‌داده‌شده توسط Vite در دسترس خواهد بود. فعلاً صفحه داشبورد نمایشی است و به API متصل نشده است.
