# AGU Virtual Ofis — texnik topshiriq

## 1. Loyiha maqsadi

AGU (Auto Gas Uzbekistan, Prins'ning O'zbekistondagi rasmiy distributori) kunlik
ravishda 35–40 ta kontragentdan (LPG/CNG jihozlarini qarzga olgan mijozlar)
to'lov qabul qiladi. Hozir bu jarayon qo'lda — kassir har kuni bir nechta
alohida hujjat (Click hisoboti, kunlik naqd-hisobot, kassa daftari) yuboradi,
va bitta odam (loyiha egasi) bularni qo'lda solishtirib, har bir kontragentning
qarz holatini hisoblaydi. Xato yoki e'tibordan chetda qolgan yozuv — moliyaviy
zararga olib kelishi mumkin.

**Maqsad**: shu jarayonni to'liq avtomatlashtiruvchi "virtual ofis" — Telegram
bot + Google Sheets + veb-dashboard. Tizim uchta inson (menejer, buxgalter,
nazoratchi) bajaradigan ishni bitta odam (loyiha egasi, pul kirimini shaxsan
kuzatadi) + bot (buxgalter va nazoratchi vazifasini avtomatik bajaradi)
ko'rinishida bajaradi. Bot hech qanday moliyaviy qarorni o'zi qabul qilmaydi —
faqat aniqlaydi, solishtiradi, signal beradi; yakuniy qaror doim odamda qoladi.

**Arxitektura qarori**: menejer/buxgalter/nazoratchi — har biri o'z vazifasiga
ega AI "agent" sifatida tasavvur qilinadi, lekin **bitta bot ichida 3 ta
alohida modul** sifatida quriladi (3 ta jismoniy alohida Telegram bot emas) —
soddalik va umumiy Google Sheets orqali tabiiy bog'lanish uchun:
- **Menejer modul** — ma'lumot qabul qiladi (fayllarni o'qiydi, foydalanuvchidan so'raydi)
- **Buxgalter modul** — solishtiradi, tekshiradi, mos kelmasa aniqlaydi
- **Nazoratchi modul** — kuzatadi, faqat kerak bo'lganda signal beradi
- **4-modul** — "Абдуллох"-formatidagi (har kontragent uchun alohida
  workbook, 31 kunlik varaq, har varaqda tovar jadvali + qarz/to'lov bloki)
  faylni qabul qiladi va undan **faqat "келган пул" bo'limini** (сум/click/
  доллар/пластик) o'qiydi — tovar jadvaliga tegmaydi. Oldingi versiya bilan
  solishtirib, faqat o'zgargan kunlarni chiqaradi (6-bo'limdagi
  tasdiqlash-oqimi bilan bir xil mantiq). **Diqqat**: bu formatda "доллар"
  so'zi uchta turli bo'limda (Карз, келган пул, колган карз) takrorlanadi —
  parser FAQAT "келган пул" satridan boshlab keyingi 4 qatorni o'qishi kerak,
  butun varaqni "доллар" so'zi bo'yicha qidirmasligi kerak (aks holda
  noto'g'ri qiymat olinadi — bu suhbatda sinab, xato tutib tuzatilgan).
  Bu format 1-kun uchun boshqa faylga bog'langan tashqi formula (Карз
  доллар) saqlaydi — bu 4-modulga xalaqit bermaydi, lekin faylni to'liq
  qayta hisoblashga (recalculate) urinilsa xatolik beradi.

## 2. Texnik stack

- **Bot**: Python, aiogram (loyiha egasida shu asosda tajriba va mavjud botlar bor)
- **Deploy**: Railway (mavjud infratuzilma, APScheduler bilan)
- **Ma'lumotlar bazasi**: Google Sheets (Sheets API, service account orqali —
  odamlar to'g'ridan-to'g'ri tahrirlamaydi, faqat bot yozadi, dashboard o'qiydi)
- **Fayl tahlili**: openpyxl / pandas (Click va hisobot fayllarini o'qish uchun)
- **1C:Enterprise 8.3**: mavjud integratsiya (BSL external processing) — oy
  oxirida yakuniy summalar shu yerga ham yoziladi

## 3. Ma'lumotlar modeli — kunlik yozuv (har kontragent, har kun)

| Maydon | Tavsif |
|---|---|
| Sana | |
| Kontragent (rasmiy ID) | Alias-jadval orqali aniqlanadi (4-bo'limga qarang) |
| Qarz — kun boshida (so'm, dollar) | Kun 1: input (dollar — o'tgan oydan, so'm — 0 dan boshlanadi). Kun >1: oldingi kunning "qolgan qarz"idan avtomatik olinadi |
| Naqd (so'm) | Kassa daftaridan / qo'lda |
| Click | Click faylidan (avtomatik) |
| Naqd (dollar) | Kassa daftaridan / qo'lda ("qog'oz pul" deb ham yuritiladi) |
| Terminal (plastik + o'tkazma) | Bitta birlashtirilgan maydon — terminal chek summasi bo'yicha |
| Chegirma (so'm) | |
| Kurs | Kuniga bitta marta so'raladi, o'sha kunning barcha yozuvlariga qo'llanadi |
| Jami qabul (som, dollar) | Formula |
| Qolgan qarz (som, dollar) | Formula — manfiy chiqsa "avans" deb ko'rsatiladi, "qarz" emas |

**Muhim qoidalar** (barchasi suhbatda tasdiqlangan):
- Qolgan qarz keyingi KUNGA — ikkala valyutada ham avtomatik o'tadi.
- Qolgan qarz keyingi OYGA — FAQAT dollarda o'tadi (hozirgi amaliyotga mos);
  so'm qarzi har oy boshida 0 dan boshlanadi.
- Oylik komissiya = jami topshirilgan pul (dollar ekvivalentida) × stavka
  (standart 1%, o'zgaruvchan katakcha sifatida, kodga qattiq yozilmaydi).
- Tovar/yuk kuzatilmaydi — bu tizim faqat pul kirimi uchun (1C bilan
  integratsiya — kelajakdagi bosqich, 8-bo'limga qarang).

## 4. Kirish manbalari — fayl formatlari (haqiqiy fayllardan tasdiqlangan)

### 4.1 Click fayli (`click_DD_MM_YYYY.xlsx`)
- 1-qator: kontragent nomlari ustun sarlavhasi sifatida (masalan `A1="Rashid aka"`)
- 2-qatordan boshlab: har bir tranzaksiya alohida qatorda, tegishli ustunda
  (bitta kontragentda bir necha tranzaksiya bo'lishi mumkin, qatorlar soni
  kunma-kun o'zgaradi)
- "Jami" qatori: **qattiq qator raqamiga bog'lanmasin** — dasturiy ravishda
  aniqlanadi (qaysi qator qiymati o'zidan yuqoridagi barcha qiymatlar
  yig'indisiga teng bo'lsa, o'sha "jami" qatori)
- Undan keyingi qator: har bir kontragentning dollar ekvivalenti
  (`jami / kurs`)
- "курс" so'zi qidiriladi, undan o'ng tarafdagi katakcha — kurs qiymati
- Ishlaydigan parser namunasi ushbu suhbatda yozilgan va real faylda sinalgan.

### 4.2 Hisobot fayli (`hisobot_DD_MM_YYYY.xlsx`)
- Boshqa yo'nalish: qatorlarda to'lov turi (`naqt`, `Qog'oz`, `Plastik`,
  `click`), ustunlarda kontragentlar
- `naqt` = naqd so'm, **`Qog'oz` = naqd dollar** (real fayllar orqali
  o'zaro solishtirib tasdiqlangan — miqyosi ham, qiymatlari ham mos keldi)
- Oxirgi ustun — har bir qatorning (to'lov turining) jami yig'indisi
  (kontragent bo'yicha jami emas!)
- Faqat "har kuni keladigan" kontragentlar shu yerda — Click faylidagi
  to'liq ro'yxatning kichik qismi

### 4.3 Kassa daftari (hozircha rasm/skrinshot ko'rinishida)
- Kirim (income) va Chiqim (expense) ustunlari
- Kirim tarafida ba'zi qatorlar kontragentlarga tegishli (naqd so'm + naqd
  dollar — hisobot faylining `naqt`+`Qog'oz` bilan bir xil), ba'zilari
  umuman aloqasiz (boshqa daromad manbalari)
- Chiqim tarafi — xarajatlar, bu tizimga aloqasi yo'q, e'tiborsiz qoldiriladi
- Agar kelajakda haqiqiy fayl (skrinshot emas) sifatida olinsa, xuddi shu
  mantiq bilan o'qiladi

## 5. Kontragent nomlarini moslashtirish (alias tizimi)

Bir xil kontragent turli faylda turlicha yozilishi tasdiqlangan (masalan
"Alisher aka agu" / "Alisher aka do'kon" — bir xil summa, bitta odam).
**Avtomatik moslashtirish (fuzzy matching) ishonchli emas** — kerak:

1. Rasmiy kontragentlar ro'yxati (ID + rasmiy nom)
2. Alias-jadval: har bir manbadagi (Click, hisobot, kassa) nom variantlari
   shu ID'ga bog'lanadi — bir martalik sozlash, keyin doim ishlaydi
3. Mos kelmagan nom chiqsa, bot **hech qachon taxmin qilmaydi** — alohida
   "qo'lda tekshiring" ro'yxatiga chiqaradi

## 6. Bot muloqot oqimi

- **Kurs** — kuniga bir marta so'raladi (birinchi kirishda), keyin shu
  kunning barcha yozuvlariga avtomatik qo'llanadi.
- **To'lov raqamlari turli vaqtda keladi** (click ertalab, naqd kechqurun
  va h.k.) — yozuv bitta sessiyada emas, **bo'lak-bo'lak to'ldiriladi**.
  Har bir kontragent uchun "to'liq" / "to'liq emas" holati ko'rinadi.
- **"Bugun to'lov yo'q" tugmasi** — bir bosishda hammasini 0 qilib keyingi
  kontragentga o'tkazadi.
- **"Tuzatish" tugmasi** — tasdiqdan keyin ham, o'sha kontragentning
  savollarini qaytadan so'raydi, eski qiymat ustidan yozadi.
- **"Kechiktirilgan kun" tugmasi** — sana tanlanadi, o'sha sanaga orqaga
  qaytib yoziladi; zanjir avtomatik qayta hisoblanadi (7-bo'limga qarang).
- **Click faylini yuklash** — fayl yuborilsa, bot avtomatik o'qib, mos
  kelgan kontragentlarga taqsimlaydi, mos kelmaganlarni ko'rsatadi.
- **Fayl qayta yuborilsa (tuzatilgan versiya) — hech qachon jim
  yozib qo'yilmaydi.** Bot: (1) yangi faylni tahlil qiladi, (2) oldingi
  natija bilan solishtiradi, (3) FAQAT o'zgargan kontragentlarni
  ko'rsatadi (eski qiymat -> yangi qiymat), (4) foydalanuvchi
  tasdiqlamaguncha Sheets'da hech narsa yangilanmaydi. Bu mexanizm real
  fayl ustida sinalgan va ishlayotgani tasdiqlangan — bitta kontragentda
  o'zgarish bo'lganda, faqat o'sha bitta qator aniqlanadi, qolgan
  hammasi tegilmaydi. Bot doim shu darajada bashorat qilinadigan va
  barqaror ishlashi kerak — hech qanday "jim" yozish yoki qayta
  hisoblash bo'lmasligi kerak.

## 7. Tarixiy tuzatish — zanjir mantig'i

Har kunning "qarz boshida" — oldingi kunning "qolgan qarz"idan formula
orqali olinadi (Google Sheets'da hujayralar bir-biriga bog'langan). Shuning
uchun o'tgan kundagi raqamni tuzatish — undan keyingi BARCHA kunlarni
avtomatik qayta hisoblaydi, qo'lda hech narsa qilish shart emas. Faqat:
kim tuzatishga huquqli (menejer emas), va tuzatilganda xabar ketishi kerak
(9-bo'limga qarang).

## 8. Bildirishnomalar

| Kimga | Qachon | Tarkib |
|---|---|---|
| Sizga | Har kiritishdan keyin | Qabul qilingan (so'm/click/terminal breakdown) + jami qabul ($) + qolgan qarz ($) |
| Sizga | Har kuni ertalab | Eng katta qarzdorlar (oy bo'yicha jami + oxirgi to'lov), to'liq ro'yxat dashboard'da |
| Sizga | Oy oxirida | Jami topshirilgan ($), komissiya, chegirmalar jami |
| Sizga | Faqat kerak bo'lsa | 3+ kun to'lovsiz; g'ayrioddiy katta chegirma; qarz belgilangan chegaradan oshsa; kontragent kunlik ro'yxatga kiritilmay qolsa; o'tgan kun tuzatilsa |

## 9. Xavfsizlik

- Faqat ro'yxatga olingan Telegram ID(lar) botga kiradi
- Har bir amal (kiritish, tuzatish, o'chirish) — kim va qachon qilgani bilan
  birga log'ga yoziladi
- G'ayrioddiy katta summa kiritilsa — bot qo'shimcha tasdiq so'raydi
- Google Sheets faqat bot (service account) orqali yoziladi

## 10. Keyingi bosqich (hozircha qamrovdan tashqari)

- Terminal chekining rasmidan OCR orqali summani avtomatik o'qish
- Tovar/yuk harakati — **1C'dan o'qib olish orqali** (qaytadan kuzatish
  emas — 1C'da allaqachon bor, ikki marta kiritishning hojati yo'q, agar
  1C ma'lumoti to'liq va ishonchli bo'lsa; buni tasdiqlash kerak)
- "Eng ko'p qarzdorlar" reytingi va tahlili

---
*Ushbu hujjat Claude bilan bo'lgan loyihalashtirish suhbati asosida
tuzilgan — barcha qoidalar shu suhbatda aniq tasdiqlangan.*
