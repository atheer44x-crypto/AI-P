from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
from openai import OpenAI

# ضع مفتاح OpenAI الجديد هنا
client = OpenAI(api_key="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")

app = Flask(__name__)

# اسم ملف الإكسل
df = pd.read_excel("z.xlsx")

df.columns = df.columns.str.strip()

COL_ENTITY = "الجهة"
COL_YEAR = "السنة"
COL_PERIOD = "الفترة"
COL_JOB = "الوظيفة"
COL_ADMIN = "الإدارة"
COL_CLASS = "تصنيف النماذج"
COL_MODEL = "النماذج"
COL_REJ_ADMIN = "النماذج المرفوضة من الإدارة"
COL_REASON_ADMIN = "سبب رفض النماذج من الإدارة"
COL_REJ_MINISTRY = "النماذج المرفوضة من الوزارة"
COL_REASON_MINISTRY = "سبب رفض النماذج من الوزارة"

df[COL_REJ_ADMIN] = pd.to_numeric(df[COL_REJ_ADMIN], errors="coerce").fillna(0)
df[COL_REJ_MINISTRY] = pd.to_numeric(df[COL_REJ_MINISTRY], errors="coerce").fillna(0)

for col in [COL_ENTITY, COL_PERIOD, COL_JOB, COL_ADMIN, COL_CLASS, COL_MODEL]:
    df[col] = df[col].astype(str).str.strip()

def normalize_text(x):
    return (
        str(x).strip()
        .replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ة", "ه")
        .replace("ى", "ي")
        .lower()
    )

def numbered_list(items):
    return "\n".join([f"{i+1}- {item}" for i, item in enumerate(items)])

def clean_values(series):
    return (
        series.dropna()
        .astype(str)
        .str.strip()
        .loc[lambda x: (x != "") & (x != "nan") & (x != "لايوجد") & (x != "لا يوجد")]
        .unique()
        .tolist()
    )

def find_model(question):
    q = normalize_text(question)

    if "اكثر" in q or "اجمالي" in q or "كم رفض" in q:
        return None

    stop_words = {
        "وش", "ماهو", "ماهي", "كم", "عدد", "نموذج", "النموذج", "النماذج",
        "رفض", "مرفوض", "تعرض", "من", "في", "خلال", "سنة", "السنة",
        "الربع", "الاول", "الثاني", "الثالث", "الرابع",
        "الاداره", "الادارة", "الوزاره", "الوزارة"
    }

    words = [w for w in q.split() if len(w) > 2 and w not in stop_words]
    models = df[COL_MODEL].dropna().unique()

    best = None
    best_score = 0

    for model in models:
        m = normalize_text(model)
        score = sum(1 for w in words if w in m)
        if score > best_score:
            best_score = score
            best = model

    return best if best_score > 0 else None

def filter_by_year_period(data, question):
    q = normalize_text(question)
    result = data.copy()

    for year in result[COL_YEAR].dropna().unique():
        if str(year) in q:
            result = result[result[COL_YEAR].astype(str) == str(year)]

    period_map = {
        "الربع الاول": "الربع الأول",
        "ربع اول": "الربع الأول",
        "الاول": "الربع الأول",
        "الربع الثاني": "الربع الثاني",
        "ربع ثاني": "الربع الثاني",
        "الثاني": "الربع الثاني",
        "الربع الثالث": "الربع الثالث",
        "ربع ثالث": "الربع الثالث",
        "الثالث": "الربع الثالث",
        "الربع الرابع": "الربع الرابع",
        "ربع رابع": "الربع الرابع",
        "الرابع": "الربع الرابع",
    }

    for key, value in period_map.items():
        if key in q:
            result = result[result[COL_PERIOD].astype(str).str.strip() == value]
            break

    return result

def mentioned_periods_from_question(question):
    q = normalize_text(question)
    periods = []

    if "الاول" in q or "ربع اول" in q:
        periods.append("الربع الأول")
    if "الثاني" in q or "ربع ثاني" in q:
        periods.append("الربع الثاني")
    if "الثالث" in q or "ربع ثالث" in q:
        periods.append("الربع الثالث")
    if "الرابع" in q or "ربع رابع" in q:
        periods.append("الربع الرابع")

    return periods

def analyze(question):
    q = normalize_text(question)
    data = filter_by_year_period(df, question)
    model = find_model(question)

    # أكثر نموذج تعرض للرفض
    if ("اكثر" in q or "أكثر" in question) and ("رفض" in q or "الرفض" in q):
        grouped = data.groupby(COL_MODEL).agg({
            COL_REJ_ADMIN: "sum",
            COL_REJ_MINISTRY: "sum"
        })

        grouped["الإجمالي"] = grouped[COL_REJ_ADMIN] + grouped[COL_REJ_MINISTRY]

        if "اداره" in q and "وزاره" in q:
            top = grouped.sort_values("الإجمالي", ascending=False).head(1)
            name = top.index[0]
            row = top.iloc[0]
            return (
                f"أكثر نموذج تعرض للرفض من الإدارة والوزارة هو: {name}\n"
                f"رفض الإدارة: {int(row[COL_REJ_ADMIN])}\n"
                f"رفض الوزارة: {int(row[COL_REJ_MINISTRY])}\n"
                f"الإجمالي: {int(row['الإجمالي'])}"
            )

        if "اداره" in q or "الاداره" in q:
            top = grouped.sort_values(COL_REJ_ADMIN, ascending=False).head(1)
            name = top.index[0]
            total = int(top.iloc[0][COL_REJ_ADMIN])
            return f"أكثر نموذج تعرض للرفض من الإدارة هو: {name}\nعدد مرات الرفض: {total}"

        if "وزاره" in q or "الوزاره" in q:
            top = grouped.sort_values(COL_REJ_MINISTRY, ascending=False).head(1)
            name = top.index[0]
            total = int(top.iloc[0][COL_REJ_MINISTRY])
            return f"أكثر نموذج تعرض للرفض من الوزارة هو: {name}\nعدد مرات الرفض: {total}"

        top = grouped.sort_values("الإجمالي", ascending=False).head(1)
        name = top.index[0]
        row = top.iloc[0]
        return (
            f"أكثر نموذج تعرض للرفض بشكل عام هو: {name}\n"
            f"رفض الإدارة: {int(row[COL_REJ_ADMIN])}\n"
            f"رفض الوزارة: {int(row[COL_REJ_MINISTRY])}\n"
            f"الإجمالي: {int(row['الإجمالي'])}"
        )

    # إجمالي رفض الإدارة حسب السنة أو الأرباع
    if ("كم" in q or "اجمالي" in q or "عدد" in q) and ("رفض" in q or "مرفوض" in q) and ("اداره" in q or "الاداره" in q):
        periods = mentioned_periods_from_question(question)

        if len(periods) >= 2 or "الارباع" in q or "الأرباع" in question:
            if not periods:
                periods = ["الربع الأول", "الربع الثاني", "الربع الثالث", "الربع الرابع"]

            result = []
            for period in periods:
                rows = df[df[COL_PERIOD].astype(str).str.strip() == period]

                for year in df[COL_YEAR].dropna().unique():
                    if str(year) in str(question):
                        rows = rows[rows[COL_YEAR].astype(str) == str(year)]

                total = int(rows[COL_REJ_ADMIN].sum())
                result.append(f"{period}: {total}")

            return "إجمالي رفض الإدارة حسب الأرباع:\n" + "\n".join(result)

        total = int(data[COL_REJ_ADMIN].sum())
        return f"إجمالي رفض الإدارة هو: {total}"

    # إجمالي رفض الوزارة حسب السنة أو الأرباع
    if ("كم" in q or "اجمالي" in q or "عدد" in q) and ("رفض" in q or "مرفوض" in q) and ("وزاره" in q or "الوزاره" in q):
        periods = mentioned_periods_from_question(question)

        if len(periods) >= 2 or "الارباع" in q or "الأرباع" in question:
            if not periods:
                periods = ["الربع الأول", "الربع الثاني", "الربع الثالث", "الربع الرابع"]

            result = []
            for period in periods:
                rows = df[df[COL_PERIOD].astype(str).str.strip() == period]

                for year in df[COL_YEAR].dropna().unique():
                    if str(year) in str(question):
                        rows = rows[rows[COL_YEAR].astype(str) == str(year)]

                total = int(rows[COL_REJ_MINISTRY].sum())
                result.append(f"{period}: {total}")

            return "إجمالي رفض الوزارة حسب الأرباع:\n" + "\n".join(result)

        total = int(data[COL_REJ_MINISTRY].sum())
        return f"إجمالي رفض الوزارة هو: {total}"

    # الجهات بدون تكرار مع ترقيم
    if "جهات" in q or "الجهات" in q or "ماهي الجهات" in q or "وش الجهات" in q:
        entities = sorted(clean_values(data[COL_ENTITY]))
        return "الجهات الموجودة بدون تكرار:\n" + numbered_list(entities)

    # الإدارات حسب كل جهة بدون تكرار
    if "ادارات" in q or "الادارات" in q or "الإدارات" in question or "ماهي الادارات" in q:
        result = []
        entities = sorted(clean_values(data[COL_ENTITY]))

        for entity in entities:
            rows = data[data[COL_ENTITY] == entity]
            admins = sorted(clean_values(rows[COL_ADMIN]))

            if admins:
                result.append(f"{entity}:")
                result.extend([f"{i+1}- {admin}" for i, admin in enumerate(admins)])
                result.append("")

        return "الإدارات الموجودة حسب كل جهة بدون تكرار:\n" + "\n".join(result)

    # مسميات النماذج بدون تكرار مع ترقيم
    if (
        "مسميات النماذج" in q
        or "اسماء النماذج" in q
        or "أسماء النماذج" in question
        or ("ماهي" in q and "النماذج" in q)
        or ("وش" in q and "النماذج" in q)
    ):
        models = sorted(clean_values(data[COL_MODEL]))
        return "مسميات النماذج الموجودة بدون تكرار:\n" + numbered_list(models)

    # عدد النماذج بدون تكرار
    if "عدد" in q and ("نموذج" in q or "النماذج" in q):
        models = clean_values(data[COL_MODEL])
        return f"عدد النماذج الموجودة بدون تكرار: {len(models)}"

    # الوظائف بدون تكرار
    if "وظيف" in q or "الوظائف" in q or "مسميات الوظائف" in q:
        jobs = sorted(clean_values(data[COL_JOB]))
        return "الوظائف الموجودة بدون تكرار:\n" + numbered_list(jobs)

    # عدد الجهات بدون تكرار
    if "عدد" in q and ("جهه" in q or "جهة" in q or "الجهات" in q):
        entities = clean_values(data[COL_ENTITY])
        return f"عدد الجهات بدون تكرار: {len(entities)}"

    # تصنيف نموذج محدد
    if model and ("تصنيف" in q or "لون" in q):
        rows = data[data[COL_MODEL] == model]
        classes = sorted(clean_values(rows[COL_CLASS]))
        return f"تصنيف نموذج {model}: {'، '.join(classes)}"

    # رفض نموذج محدد من الإدارة
    if model and ("اداره" in q or "الاداره" in q):
        rows = data[data[COL_MODEL] == model]
        total = int(rows[COL_REJ_ADMIN].sum())
        return f"إجمالي رفض نموذج {model} من الإدارة: {total}"

    # رفض نموذج محدد من الوزارة
    if model and ("وزاره" in q or "الوزاره" in q):
        rows = data[data[COL_MODEL] == model]
        total = int(rows[COL_REJ_MINISTRY].sum())
        return f"إجمالي رفض نموذج {model} من الوزارة: {total}"

    # عرض النماذج حسب التصنيف: أحمر / أصفر / أخضر
    if "تصنيف" in q or "مصنفه" in q or "مصنفة" in question or "احمر" in q or "اصفر" in q or "اخضر" in q:
        wanted_class = None

        if "احمر" in q:
            wanted_class = "أحمر"
        elif "اصفر" in q:
            wanted_class = "أصفر"
        elif "اخضر" in q:
            wanted_class = "أخضر"

        if wanted_class:
            rows = data[data[COL_CLASS].astype(str).str.strip() == wanted_class]
            models = sorted(clean_values(rows[COL_MODEL]))

            if not models:
                return f"لا توجد نماذج مصنفة باللون {wanted_class}."

            return f"النماذج المصنفة باللون {wanted_class}:\n" + numbered_list(models)

        counts = data[COL_CLASS].value_counts()
        return "توزيع التصنيفات:\n" + "\n".join([f"- {k}: {v}" for k, v in counts.items()])

    total_admin = int(data[COL_REJ_ADMIN].sum())
    total_ministry = int(data[COL_REJ_MINISTRY].sum())
    models_count = len(clean_values(data[COL_MODEL]))
    entities_count = len(clean_values(data[COL_ENTITY]))
    jobs_count = len(clean_values(data[COL_JOB]))

    return f"""
ملخص عام:
* عدد السجلات: {len(data)}
* عدد الجهات بدون تكرار: {entities_count}
* عدد النماذج بدون تكرار: {models_count}
* عدد الوظائف بدون تكرار: {jobs_count}
* إجمالي رفض الإدارة: {total_admin}
* إجمالي رفض الوزارة: {total_ministry}
"""

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/<path:filename>")
def files(filename):
    return send_from_directory(".", filename)

@app.route("/ask", methods=["POST"])
def ask():
    try:
        question = request.json.get("question", "").strip()

        if not question:
            return jsonify({"error": "لم يتم إدخال سؤال"}), 400

        result = analyze(question)

        prompt = f"""
أنت مساعد ذكي لأمانة منطقة حائل.
خاطب المستخدم بكلمة "سعادتك".
أعد صياغة النتيجة التالية بالعربية بشكل واضح ومختصر.
حافظ على الترقيم والقوائم كما هي.
لا تضف أي أرقام من عندك.

سؤال المستخدم:
{question}

نتيجة تحليل pandas:
{result}
"""

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        answer = response.choices[0].message.content
        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)