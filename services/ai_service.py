"""Learning-path generation with Groq's FREE API (Llama models).
If no key is set, or the call fails, a built-in free fallback plan is used."""
import json, os

MODEL = "llama-3.3-70b-versatile"


def _fallback_plan(name, roles):
    top = roles[0]
    gaps = top["gaps"][:5] or ["advanced projects"]
    steps = [
        {"title": f"Learn {g}", "description": f"Study the basics of {g} using free resources (official docs, freeCodeCamp, YouTube) and practice daily.", "weeks": 2}
        for g in gaps
    ]
    steps.append({"title": f"Build a {top['role']} portfolio project",
                  "description": "Combine your new skills into one real project and publish it on GitHub.", "weeks": 3})
    steps.append({"title": "Apply for internships",
                  "description": "Polish your resume and LinkedIn, then apply with your project links.", "weeks": 1})
    return {
        "summary": f"{name}, your profile fits {top['role']} best. Here is a free, step-by-step path.",
        "roles": [{"title": r["role"], "why": f"Matches {len(r['have'])} of your skills.", "skill_gaps": r["gaps"][:5]} for r in roles],
        "steps": steps,
    }


def generate_plan(name, skills, interests, roles):
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return _fallback_plan(name, roles)
    try:
        from groq import Groq
        client = Groq(api_key=key)
        prompt = (
            "You are a career mentor for interns. Use only FREE learning resources.\n"
            f"Intern: {name}\nSkills: {skills}\nInterests: {interests}\n"
            f"Roles ranked by an ML model (with skill gaps): {json.dumps(roles)}\n\n"
            "Return ONLY valid JSON with this shape:\n"
            '{"summary": "2 sentences", '
            '"roles": [{"title": "", "why": "", "skill_gaps": ["" ]}], '
            '"steps": [{"title": "", "description": "", "weeks": 2}]}\n'
            "Give 3 roles and 6-8 ordered learning steps (courses, projects, free resources)."
        )
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.5,
        )
        data = json.loads(resp.choices[0].message.content)
        if not data.get("steps"):
            raise ValueError("no steps")
        return data
    except Exception as e:  # keep the app working on any API error
        print("Groq error, using fallback:", e)
        return _fallback_plan(name, roles)
