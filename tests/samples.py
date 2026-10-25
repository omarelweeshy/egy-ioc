"""Invented messages in the style of real Egyptian scams.

Every phone number, handle and domain here is made up. Domains use the reserved .test TLD where
the test doesn't depend on a real domain (shorteners, official brand sites).
"""

SAMPLES: tuple[str, ...] = (
    # Account "suspended" + small fee + wallet + phishing link + OTP request
    "عميلنا العزيز، تم إيقاف حسابك على إنستاباي. لإعادة التفعيل ادفع ٦ جنيه على فودافون كاش "
    "٠١٠٠ ٠٠٠ ٠٠٠١\nاو ادخل على الرابط hxxps://instapay-verify[.]test/login "
    "وابعتلي الكود اللي جالك",
    # Fake prize + malicious app + shortener
    "مبروك كسبت 5 آلاف جنيه من البنك الأهلي! نزل التطبيق NBE_update.apk من bit.ly/3xYz",
    # Wrong-transfer refund scam, Franco-Arab
    "ana 7awelt lek 1500 EGP bel ghalat, raga3hom 3ala InstaPay omar.test@instapay aw kalemni "
    "+20 11 0000 0002",
    # WhatsApp account takeover, English
    "Hi it's me, I sent you a code by mistake, can you send me the code please? wa.me/201200000003",
    # Fake traffic fine, Digital Egypt lookalike on free hosting
    "مصر الرقمية: عليك مخالفة مرور بقيمة 350ج. سدد الآن قبل الغرامة "
    "https://digital-egypt-pay.vercel.app/fine",
    # Fake aid grant, tatweel and diacritics to dodge filters
    "منحـــة تَكافُل وكَرامة ١٠٠٠ جنيه، ابعت رقمك القومي على واتساب ٠١٥٥٥٥٥٠٠٠٤",
    # Legit-looking bank OTP message (should NOT raise otp_request)
    "رمز التحقق الخاص بك هو 482913. لا تشارك هذا الرمز مع أي شخص. "
    "Do not share this code with anyone.",
    # Homoglyph link with Cyrillic letters and an email lookalike
    "Your CIB account is locked. Verify at https://cіbeg-secure.test "
    "or mail support@cibeg-help.test",
    # Real official domain mentioned (should not be flagged as a lookalike)
    "تقدر تتأكد من أي عرض على الموقع الرسمي www.cibeg.com أو من خلال تطبيق البنك",
    # Rental deposit scam, foreign number, Arabic letters touching digits
    "الشقة متاحة، ادفع العربون 10,000 جنيه على رقم01000000005 أو كلم المالك +44 7700 900123",
    # A link whose real host hides after "@" (userinfo trick)
    "Update your InstaPay: https://instapay.eg@ipn-update.test/login",
)
