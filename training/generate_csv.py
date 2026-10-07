import csv, random
from pathlib import Path
from prepare_datasets import MULTI_DOMAIN_KNOWLEDGE

csv_path = Path(__file__).parent / "interview_dataset_master.csv"

rows = []
fieldnames = ["domain", "target_role", "question_type", "question", "good_star_answer", "average_answer", "poor_answer", "keywords", "quality_score_good", "quality_score_avg", "quality_score_poor"]

templates = [
    ("technical", "Could you walk me through your hands-on methodology for {topic}?"),
    ("compliance", "How do you ensure strict quality, safety, and compliance standards when managing {topic}?"),
    ("project", "Tell me about a challenging real-world project or case where you utilized {topic}."),
    ("metrics", "What key performance metrics and indicators do you track when evaluating {topic}?"),
    ("troubleshooting", "How do you handle unexpected setbacks, critical risks, or edge cases in {topic}?"),
    ("collaboration", "Describe how you collaborate across multidisciplinary teams to execute {topic}."),
]

for d in MULTI_DOMAIN_KNOWLEDGE:
    domain = d["domain"]
    roles = d["roles"]
    degrees = d["degrees"]
    bundles = d["skill_bundles"]

    # 1. Core QA pairs
    for qa in d["qa_pairs"]:
        for r in roles:
            rows.append({
                "domain": domain,
                "target_role": r,
                "question_type": "core_competency",
                "question": qa["question"],
                "good_star_answer": qa["good"],
                "average_answer": qa["medium"],
                "poor_answer": qa["poor"],
                "keywords": ", ".join(qa["keywords"]),
                "quality_score_good": 4.8,
                "quality_score_avg": 2.8,
                "quality_score_poor": 1.0,
            })

    # 2. Augmented rows
    for _ in range(150):
        r = random.choice(roles)
        deg = random.choice(degrees)
        bundle = random.choice(bundles)
        skill = random.choice(bundle)
        q_type, tmpl = random.choice(templates)
        years = random.randint(2, 9)

        q_text = tmpl.format(topic=skill)
        good_ans = (
            f"As a {r} holding a degree in {deg} with {years}+ years of experience, I approach {skill} using systematic, evidence-based practices. "
            f"In a major initiative, I took ownership of our {skill} workflow, instituted verified quality checklists, and aligned multidisciplinary stakeholders. "
            f"This proactive execution elevated operational efficiency by {random.randint(15, 38)}% and maintained 100% compliance with industry standards."
        )
        med_ans = (
            f"I have around {years} years of hands-on experience handling {skill} in my role as a {r}. "
            f"I follow the standard operating procedures and coordinate with my colleagues whenever complex issues arise to ensure tasks are completed."
        )
        poor_ans = (
            f"I have seen {skill} used before in our department. If given the assignment, I can carry it out following basic instructions."
        )

        rows.append({
            "domain": domain,
            "target_role": r,
            "question_type": q_type,
            "question": q_text,
            "good_star_answer": good_ans,
            "average_answer": med_ans,
            "poor_answer": poor_ans,
            "keywords": f"{skill.lower()}, {domain.lower()}, methodology, quality, results",
            "quality_score_good": round(random.uniform(4.5, 4.9), 2),
            "quality_score_avg": round(random.uniform(2.4, 3.1), 2),
            "quality_score_poor": round(random.uniform(0.7, 1.3), 2),
        })

random.shuffle(rows)

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {len(rows)} real CSV rows at {csv_path}")
