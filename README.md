# BlackBox Twin

> **סטטוס:** קונספט ראשוני. המערכת עדיין לא פותחה — ההיתכנות הטכנית והבידול המסחרי עדיין בבדיקה.

**BlackBox Twin** היא מערכת שלומדת את ההתנהגות של שירות או מכשיר דרך התקשורת שלו, גם בלי גישה לקוד המקור, ובונה תאום דיגיטלי (Digital Twin) שאפשר להריץ ולבדוק מולו תוכנה.

## הבעיה

בארגונים יש שרתים, ציוד תעשייתי, מערכות Legacy ומכשירים שאין גישה לקוד המקור שלהם או לתיעוד מדויק של הפרוטוקול. זה מקשה על צוותי פיתוח ו-QA לבדוק אינטגרציות בלי המכשיר המקורי, לדמות שגיאות נדירות ולהריץ בדיקות אוטומטיות בסביבה מבודדת.

## הפתרון המוצע

1. **Capture / Import** — קליטת הקלטות תעבורה מורשות (PCAP או Trace).
2. **Protocol Discovery** — חילוץ הודעות, שדות ומזהי פעולות.
3. **Behavior Learning** — הסקת מכונת מצבים (State Machine) ולא רק מיפוי בקשה→תשובה.
4. **Active Learning** — בחירת ניסויים מורשים שמצמצמים אי-ודאות.
5. **Twin Generation** — הפקת שרת וירטואלי שרץ ב-Docker.
6. **Differential Testing** — הרצת אותם רצפים מול המקור ומול התאום והשוואת התוצאות.
7. **Confidence & Coverage** — דוח שמראה מה עובד, מה לא, ומה עדיין לא נבדק.
8. **Fault Simulation** — הזרקת שגיאות, השהיות וניתוקים לתאום בלבד.

## ארכיטקטורה (מוצעת)

```text
Authorized Device / Lab Server
             |
             v
    Traffic Capture / PCAP
             |
             v
       Session Parser
             |
             v
   Message Type Inference
             |
             v
     State Model Learner <---- Active Probe Planner
             |                       |
             |               Approved Lab Tests
             +-----------------------+
             |
             v
         Twin Builder
             |
             v
    Dockerized Twin Server
             |
             v
   Differential Test Runner <---- Original Device
             |
             v
    Coverage / Confidence UI
```

## יעד ה-MVP

להוכיח שאפשר ללמוד התנהגות תלוית-מצב של שירות **TCP** יחיד בסביבה מבוקרת (4–6 פעולות, 3–5 מצבים), להפיק תאום, ולהשיג התאמה טובה על **רצפי בדיקה שלא הופיעו באימון** — בהשוואה ל-Baseline של Record & Replay.

## טכנולוגיות אפשריות (לא סופי)

Python · Scapy · FastAPI · Docker · React / Next.js · SQLite → PostgreSQL · NetworkX · LLM (אופציונלי, לא כראיה לאימות)

## מדדי הצלחה

- Unseen Sequence Accuracy
- State Transition Coverage
- Message Coverage
- Discovery Efficiency
- False Confidence
- Twin Build Time

## תכנית פיתוח

| שלב | מטרה |
|---|---|
| A | הוכחת היתכנות — שרת TCP ניסויי עם מכונת מצבים מוסתרת, Client ו-Traces |
| B | למידה ויצירת תאום — זיהוי הודעות, מודל מצבים, Twin Server |
| C | הוכחה ולא רק דמו — בדיקות דיפרנציאליות, כיסוי, השוואה ל-Record & Replay |
| D | בידול — Active Learning, דומיין אמיתי אחד, סט תרחישים מצטבר |

## בטיחות והרשאות

- ניסויים אקטיביים רק במעבדה מורשית, עם Allowlist של פקודות, Rate Limit וכפתור עצירה.
- אין ניסויים מול ציוד של צד שלישי ללא אישור מפורש.
- אין פענוח של תעבורה מוצפנת ללא הרשאה.

## מסמכים

- [INSTRUCTIONS.md](INSTRUCTIONS.md) — **איך עובדים עם הפרויקט**: התקנה, הרצה, בדיקות, הרצה ידנית של כל חלק, ושלבי AWS IoT Core.
- [docs/BlackBox_Twin_Project_Report.docx](docs/BlackBox_Twin_Project_Report.docx) — **דוח הפרויקט** (Word, בעברית): מה עשינו, מה עובד ואיך זה עובד.
- [presentation/](presentation/README.md) — **המצגת** (PDF ו-HTML): איך זה עובד ומה ה-POC הוכיח.
- [poc/README.md](poc/README.md) — **POC שרץ**: לומד מכשיר מדומה, בונה תאום ומשווה ל-Record & Replay. מריצים: `python poc/run_demo.py`.
- [docs/POC_PLAN.md](docs/POC_PLAN.md) — תוכנית ה-POC: ESP32 + AWS IoT Core, מכונת המצבים, ארכיטקטורה ואבני דרך.
- [docs/SIMPLE_EXPLANATION.md](docs/SIMPLE_EXPLANATION.md) — הסבר פשוט על הפרויקט.
- [BLACKBOX_TWIN_CONTEXT.md](BLACKBOX_TWIN_CONTEXT.md) — מסמך הקונטקסט המלא של הפרויקט (רעיון, MVP, סיכונים, שאלות פתוחות והנחיות לכלי AI).

---

> לא מספיק ליצור תוכנה שנראית כמו המכשיר. צריך למדוד באילו מצבים התאום באמת מתנהג כמוהו, ולדעת לומר מתי אנחנו עדיין לא יודעים.
