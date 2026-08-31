<div dir="rtl">

# התקנה ב-Claude Desktop (Cowork)

**רגע — משתמשים ב-Cowork? יש גרסה שנכתבה בשבילו:**
[agentic-media-stack-cowork](https://github.com/LeonMelamud/agentic-media-stack-cowork).
הכישורים במאגר הזה מריצים כלים מקומיים (טרמינל, ffmpeg, התקנות), ולכן ב-Cowork ההוראה הראשונה
שלהם היא משהו שאי אפשר לבצע. הגרסה השנייה עושה הכול דרך מודלים מרוחקים — בלי טרמינל ובלי התקנות.

המדריך שלמטה מתאים למי שרוצה בכל זאת להעלות דווקא את המאגר הזה ל-Claude Desktop.

מדריך קצר: מורידים ZIP מגיטהאב, מעלים אותו ב-Cowork. בלי טרמינל, בלי חשבון גיטהאב.

## שלב 1 — להוריד את ה-ZIP מגיטהאב

לחצו על הקישור הזה, וההורדה מתחילה לבד:

</div>

**https://github.com/LeonMelamud/agentic-media-stack/archive/refs/heads/main.zip**

<div dir="rtl">

או ידנית: נכנסים ל-[github.com/LeonMelamud/agentic-media-stack](https://github.com/LeonMelamud/agentic-media-stack), לוחצים על הכפתור הירוק **Code** ואז **Download ZIP**.

הקובץ שיורד נקרא `agentic-media-stack-main.zip`.

**חשוב: לא לפתוח את ה-ZIP.** מעלים את הקובץ עצמו.
בספארי יש הגדרה שפותחת קבצים אוטומטית. אם במקום קובץ ZIP קיבלתם תיקייה — לחצו עליה ימני ואז **Compress**, וקיבלתם ZIP תקין להעלאה. אפשר גם פשוט להוריד ב-Chrome.

## שלב 2 — להעלות ב-Cowork

1. פותחים את אפליקציית **Claude Desktop**
2. **Settings** (הגדרות)
3. בתפריט הצד — **Cowork** ואז **Plugins**
   אם לא מוצאים: כותבים `Plugins` בשורת החיפוש של ההגדרות למעלה
4. לוחצים **Upload plugin**
5. גוררים לחלון את `agentic-media-stack-main.zip` (או לוחצים ובוחרים אותו)
6. לוחצים **Upload**

תופיע אזהרה של Anthropic שהתוסף אינו שלהם ושצריך לתת בו אמון — זה תקין, זה מופיע לכל תוסף שמעלים ידנית.

## שלב 3 — לבדוק שזה עובד

פותחים צ'אט חדש ב-Cowork וכותבים:

> I want to make a video

אם התוסף נטען, קלוד ייכנס למצב המודרך (`easy-media`): שואל שאלה אחת בכל פעם, ומעדיף כלים חינמיים שרצים על המחשב.

## עדכון לגרסה חדשה

מורידים ZIP חדש (אותו קישור) ומעלים שוב באותו מסך. הגרסה החדשה מחליפה את הישנה.

## תקלות

**"Plugin failed validation with 1 error" / "plugin.json must be at .claude-plugin/plugin.json"**
זה ZIP ישן. הבעיה תוקנה בגרסה 0.9.1 — מורידים מחדש מהקישור למעלה ומעלים שוב.

**העליתם תיקייה ולא קובץ**
ההעלאה מקבלת קובץ `.zip` בלבד.

**התוסף עלה אבל קלוד לא מגיב לכישורים**
סוגרים ופותחים את Claude Desktop, ופותחים צ'אט חדש.

## אפשרות שנייה — Claude Code בטרמינל

</div>

```bash
claude plugin marketplace add LeonMelamud/agentic-media-stack
claude plugin install agentic-media-stack@media-stack
```

<div dir="rtl">

מי שכבר הוסיף את ה-marketplace לפני 30.8.2026 — צריך לרענן קודם:

</div>

```bash
claude plugin marketplace update media-stack
```

<div dir="rtl">

## מה מקבלים

שבעה כישורים (skills) שמלמדים את קלוד להפיק וידאו, דפי נחיתה, מצגות וגרפיקה בתנועה — ולבדוק את עצמו לפני שהוא מציג תוצאה. הפירוט המלא ב-[README](README.md) וב-[PLUGIN.md](PLUGIN.md).

</div>
