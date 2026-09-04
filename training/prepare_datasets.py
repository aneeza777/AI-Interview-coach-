"""
Dataset Preparation Script
===========================
Downloads and prepares datasets for fine-tuning:
1. Interview question generation (resume/context → question)
2. Answer quality evaluation (answer + keywords → quality score)
3. Confidence classification (synthetic labels from audio features)

Datasets used:
- HuggingFace interview QA datasets
- SQuAD-style question generation data
- Custom synthetic data for answer scoring
"""

import os
import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


# ──────────────────────────────────────────────
# 1. Interview Question Generation Dataset
# ──────────────────────────────────────────────
def prepare_question_generation_dataset():
    """
    Prepare dataset for fine-tuning question generation.
    Format: {context: "resume text / job info", question: "interview question"}

    Uses a combination of:
    - HuggingFace datasets (SQuAD for question generation patterns)
    - Custom interview-specific data
    """
    print("=" * 50)
    print("Preparing Question Generation Dataset")
    print("=" * 50)

    samples = []

    # ── Part A: Custom interview question templates (high quality) ──
    # These serve as seed data for the model to learn interview patterns

    interview_patterns = [
        # (context_type, context, question)
        ("technical_python", "Skills: Python, Django, REST APIs", "Can you explain how Django's ORM handles database queries and what N+1 query problem is?"),
        ("technical_python", "Skills: Python, Flask, microservices", "How would you design a RESTful API using Flask? Walk me through your approach."),
        ("technical_python", "Skills: Python, pandas, data analysis", "How do you handle missing data in a pandas DataFrame? What strategies do you use?"),
        ("technical_react", "Skills: React, TypeScript, Next.js", "Explain the difference between useEffect and useLayoutEffect in React."),
        ("technical_react", "Skills: React, Redux, state management", "How do you manage global state in a large React application?"),
        ("technical_ml", "Skills: Machine Learning, TensorFlow, NLP", "What is overfitting and how do you prevent it in a neural network?"),
        ("technical_ml", "Skills: Deep Learning, PyTorch, Computer Vision", "Explain the architecture of a CNN and when you'd use it."),
        ("technical_database", "Skills: PostgreSQL, MongoDB, Redis", "When would you choose a NoSQL database over a relational one?"),
        ("technical_devops", "Skills: Docker, Kubernetes, CI/CD", "Describe how you would set up a CI/CD pipeline from scratch."),
        ("technical_cloud", "Skills: AWS, Lambda, S3, DynamoDB", "How would you design a serverless architecture for a web application?"),

        ("behavioral_leadership", "Experience: 3 years, Team Lead", "Tell me about a time you had to make a difficult decision as a team lead."),
        ("behavioral_conflict", "Experience: 2 years, cross-functional teams", "Describe a situation where you disagreed with a colleague's approach. How did you handle it?"),
        ("behavioral_failure", "Experience: Software Engineer, startup", "Tell me about a project that failed. What did you learn from it?"),
        ("behavioral_pressure", "Experience: 4 years, multiple deadlines", "How do you prioritize when you have multiple urgent tasks?"),
        ("behavioral_growth", "Experience: Junior developer, 1 year", "Where do you see yourself growing technically in the next 2 years?"),

        ("job_software_engineer", "Job Title: Software Engineer", "Describe your approach to writing clean, testable code."),
        ("job_data_scientist", "Job Title: Data Scientist", "How do you validate whether your model generalizes well to unseen data?"),
        ("job_frontend", "Job Title: Frontend Developer", "How do you ensure your web application is accessible to all users?"),
        ("job_backend", "Job Title: Backend Developer", "How do you handle database migrations in a production environment?"),
        ("job_devops", "Job Title: DevOps Engineer", "What monitoring and alerting strategies do you use for production systems?"),
    ]

    for pattern_type, context, question in interview_patterns:
        samples.append({
            "context": context,
            "question": question,
            "category": pattern_type.split("_")[0],
            "source": "custom_interview",
        })

    # ── Part B: Generate augmented variations ──
    # Vary skill combinations to create more training data

    skill_sets = [
        ["Python", "Django", "PostgreSQL"],
        ["JavaScript", "React", "Node.js"],
        ["Java", "Spring Boot", "MySQL"],
        ["Python", "TensorFlow", "scikit-learn"],
        ["Go", "Docker", "Kubernetes"],
        ["TypeScript", "Angular", "MongoDB"],
        ["C++", "algorithms", "data structures"],
        ["Python", "FastAPI", "Redis"],
        ["Swift", "iOS", "Core Data"],
        ["Kotlin", "Android", "Room"],
        ["Python", "pandas", "NumPy", "matplotlib"],
        ["React Native", "Firebase", "Redux"],
        ["Rust", "systems programming", "WebAssembly"],
        ["PHP", "Laravel", "Vue.js"],
        ["Ruby", "Rails", "Sidekiq"],
    ]

    question_templates = [
        "Explain your experience with {skill}. What projects have you built?",
        "What are the most important concepts in {skill} that a developer should master?",
        "How would you debug a performance issue involving {skill}?",
        "Describe a challenging problem you solved using {skill}.",
        "How do you keep up with updates and best practices in {skill}?",
        "What are the trade-offs when using {skill} versus its alternatives?",
        "How has {skill} evolved in recent years and what trends do you see?",
        "Walk me through how {skill} works under the hood.",
    ]

    for skills in skill_sets:
        skill_str = f"Skills: {', '.join(skills)}"
        for skill in skills[:3]:
            for template in random.sample(question_templates, min(3, len(question_templates))):
                q = template.format(skill=skill)
                samples.append({
                    "context": skill_str,
                    "question": q,
                    "category": "technical",
                    "source": "augmented",
                })

    # ── Part C: Try to download HuggingFace dataset ──
    try:
        from datasets import load_dataset

        print("Downloading SQuAD dataset for question patterns...")
        squad = load_dataset("squad", split="train[:5000]")

        for item in squad:
            samples.append({
                "context": item["context"][:200],  # truncate for brevity
                "question": item["question"],
                "category": "general",
                "source": "squad",
            })
        print(f"  Added {len(squad)} SQuAD samples.")
    except Exception as e:
        print(f"  Could not download SQuAD: {e} (continuing with custom data)")

    # ── Save ──
    output_path = DATA_DIR / "question_generation_dataset.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2, ensure_ascii=False)

    print(f"  Total samples: {len(samples)}")
    print(f"  Saved to: {output_path}")
    return samples


# ──────────────────────────────────────────────
# 2. Answer Quality Evaluation Dataset
# ──────────────────────────────────────────────
def prepare_answer_evaluation_dataset():
    """
    Prepare dataset for fine-tuning answer quality scoring.
    Format: {question, answer, keywords, quality_score (0-5), quality_label}

    Uses synthetic data + known good/bad answer patterns.
    """
    print("\n" + "=" * 50)
    print("Preparing Answer Evaluation Dataset")
    print("=" * 50)

    samples = []

    # ── High-quality answer examples ──
    good_answers = [
        {
            "question": "Tell me about yourself.",
            "answer": "I'm a software engineer with 3 years of experience specializing in full-stack development. I graduated from FAST University with a degree in Computer Science. In my current role at TechCorp, I've led the development of two major products using React and Python. I'm passionate about building scalable systems and mentoring junior developers.",
            "keywords": ["experience", "education", "skills", "passion", "career"],
            "quality_score": 4.5,
        },
        {
            "question": "Explain your experience with Python.",
            "answer": "I've been working with Python for 4 years now. I started with data analysis using pandas and NumPy, then moved to web development with Django and FastAPI. In my last project, I built a microservices architecture handling 10,000 requests per second. I also contributed to open-source Python libraries and regularly use pytest for testing.",
            "keywords": ["python", "project", "experience", "developed", "application"],
            "quality_score": 4.8,
        },
        {
            "question": "How do you handle tight deadlines?",
            "answer": "I approach tight deadlines by first breaking down the work into priority tiers. I communicate early with stakeholders about what's achievable and what might need to be deferred. For example, last quarter we had a critical launch — I organized daily standups, delegated effectively, and we shipped on time by focusing on core features first.",
            "keywords": ["deadline", "prioritize", "communicate", "deliver", "manage"],
            "quality_score": 4.5,
        },
        {
            "question": "What is REST API and how do you design one?",
            "answer": "REST stands for Representational State Transfer. When designing a REST API, I follow these principles: use proper HTTP methods like GET for reading, POST for creating, PUT for updating, and DELETE for removing resources. I use meaningful status codes, implement pagination for large datasets, version my APIs, and always include proper error handling with descriptive messages. I also use JSON as the data format and implement authentication using JWT tokens.",
            "keywords": ["rest", "api", "endpoint", "http", "json", "status", "route"],
            "quality_score": 4.7,
        },
        {
            "question": "Describe a challenging project.",
            "answer": "Last year, I led the migration of our monolithic application to microservices. The biggest challenge was maintaining data consistency across services. I implemented an event-driven architecture using RabbitMQ, created a comprehensive testing strategy, and we migrated incrementally over 3 months. The result was a 60% improvement in deployment speed and much better scalability.",
            "keywords": ["challenge", "problem", "solution", "result", "approach", "learned"],
            "quality_score": 4.9,
        },
    ]

    # ── Medium-quality answers ──
    medium_answers = [
        {
            "question": "Tell me about yourself.",
            "answer": "I'm a developer. I know Python and JavaScript. I've worked at a couple of companies. I like coding and learning new things.",
            "keywords": ["experience", "education", "skills", "passion", "career"],
            "quality_score": 2.5,
        },
        {
            "question": "Explain your experience with React.",
            "answer": "I've used React for about a year. I know hooks and components. I've built a few projects with it. It's a good library for frontend.",
            "keywords": ["react", "project", "hooks", "components", "experience"],
            "quality_score": 2.3,
        },
        {
            "question": "What are your strengths?",
            "answer": "I'm good at problem solving and I work hard. I learn quickly and I'm a team player.",
            "keywords": ["strength", "skill", "teamwork", "communication", "problem"],
            "quality_score": 2.0,
        },
        {
            "question": "How do you handle conflicts in a team?",
            "answer": "I try to talk to people and understand their perspective. Usually we can find a compromise. Communication is important.",
            "keywords": ["communication", "listen", "understand", "compromise", "resolve"],
            "quality_score": 2.8,
        },
    ]

    # ── Low-quality answers ──
    poor_answers = [
        {
            "question": "Tell me about yourself.",
            "answer": "Um, I don't know, I just like computers I guess.",
            "keywords": ["experience", "education", "skills", "passion", "career"],
            "quality_score": 0.8,
        },
        {
            "question": "Explain your experience with Python.",
            "answer": "Yeah, I've used Python. It's a programming language. I wrote some code with it.",
            "keywords": ["python", "project", "experience", "developed", "application"],
            "quality_score": 0.7,
        },
        {
            "question": "Describe a challenging project.",
            "answer": "Uh, I can't really think of one right now. Maybe there was something but I don't remember.",
            "keywords": ["challenge", "problem", "solution", "result", "approach"],
            "quality_score": 0.5,
        },
        {
            "question": "What is machine learning?",
            "answer": "It's like when computers learn stuff. I think it uses data or something.",
            "keywords": ["supervised", "unsupervised", "algorithm", "data", "train", "model", "predict"],
            "quality_score": 0.6,
        },
    ]

    samples.extend(good_answers)
    samples.extend(medium_answers)
    samples.extend(poor_answers)

    # ── Augment with keyword variations ──
    augment_templates = [
        {
            "question": "What is your experience with {topic}?",
            "good": "I have {years} years of experience with {topic}. In my most recent project, I used {topic} to build a scalable solution that handled thousands of users. I'm comfortable with both the fundamentals and advanced concepts like {advanced}.",
            "poor": "I know {topic} a bit. I've used it sometimes.",
            "topics": [
                ("Docker", "3", "container orchestration, multi-stage builds"),
                ("AWS", "2", "Lambda, auto-scaling, CloudFormation"),
                ("machine learning", "4", "feature engineering, model deployment, A/B testing"),
                ("database design", "3", "normalization, indexing strategies, query optimization"),
                ("agile methodology", "2", "sprint planning, retrospectives, continuous delivery"),
            ],
        },
    ]

    for template_group in augment_templates:
        for topic, years, advanced in template_group["topics"]:
            # Good answer
            samples.append({
                "question": template_group["question"].format(topic=topic),
                "answer": template_group["good"].format(topic=topic, years=years, advanced=advanced),
                "keywords": [topic.lower(), "experience", "project", "build", "advanced"],
                "quality_score": 4.2 + random.uniform(-0.3, 0.3),
            })
            # Poor answer
            samples.append({
                "question": template_group["question"].format(topic=topic),
                "answer": template_group["poor"].format(topic=topic),
                "keywords": [topic.lower(), "experience", "project", "build", "advanced"],
                "quality_score": 1.0 + random.uniform(-0.2, 0.3),
            })

    # ── Save ──
    output_path = DATA_DIR / "answer_evaluation_dataset.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2, ensure_ascii=False)

    print(f"  Total samples: {len(samples)}")
    print(f"  Saved to: {output_path}")
    return samples


# ──────────────────────────────────────────────
# 3. Confidence Classification Dataset (Labels)
# ──────────────────────────────────────────────
def prepare_confidence_dataset():
    """
    Generate labeled training data for confidence classification.
    Since we don't have real labeled audio, we define the feature ranges
    and labels that the classifier should learn.

    This creates synthetic feature vectors with confidence labels.
    """
    print("\n" + "=" * 50)
    print("Preparing Confidence Classification Dataset")
    print("=" * 50)

    import numpy as np

    samples = []

    # Feature vector: [wpm, pitch_cv, pause_ratio, volume_cv, num_pauses_per_min]
    # Labels: 0=nervous, 1=moderate, 2=confident

    # Confident speakers: 120-160 WPM, good pitch variation, few pauses
    for _ in range(200):
        features = [
            np.random.uniform(120, 160),   # wpm
            np.random.uniform(0.08, 0.25), # pitch_cv
            np.random.uniform(0.05, 0.15), # pause_ratio
            np.random.uniform(0.15, 0.30), # volume_cv
            np.random.uniform(1, 4),       # pauses_per_min
        ]
        samples.append({"features": features, "label": 2, "label_text": "confident"})

    # Moderate: slightly off ideal ranges
    for _ in range(200):
        features = [
            np.random.uniform(100, 180),   # wpm (wider range)
            np.random.uniform(0.05, 0.15), # pitch_cv (moderate)
            np.random.uniform(0.15, 0.25), # pause_ratio
            np.random.uniform(0.30, 0.50), # volume_cv
            np.random.uniform(4, 8),       # pauses_per_min
        ]
        samples.append({"features": features, "label": 1, "label_text": "moderate"})

    # Nervous: very fast/slow, monotone, many pauses
    for _ in range(200):
        features = [
            np.random.choice([
                np.random.uniform(60, 100),   # too slow
                np.random.uniform(180, 240),   # too fast
            ]),
            np.random.uniform(0.02, 0.06),  # monotone
            np.random.uniform(0.25, 0.45),  # many pauses
            np.random.uniform(0.50, 0.80),  # inconsistent volume
            np.random.uniform(8, 15),       # many pauses
        ]
        samples.append({"features": features, "label": 0, "label_text": "nervous"})

    # Shuffle
    random.shuffle(samples)

    # ── Save ──
    output_path = DATA_DIR / "confidence_classification_dataset.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2)

    print(f"  Total samples: {len(samples)}")
    print(f"  Saved to: {output_path}")
    return samples


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🔧 AI Interview Coach — Dataset Preparation\n")

    prepare_question_generation_dataset()
    prepare_answer_evaluation_dataset()
    prepare_confidence_dataset()

    print("\n✅ All datasets prepared!")
    print(f"   Output directory: {DATA_DIR}")
    print("\nNext step: Run the training scripts:")
    print("   py train_question_generator.py")
    print("   py train_answer_evaluator.py")
    print("   py train_confidence_classifier.py")
