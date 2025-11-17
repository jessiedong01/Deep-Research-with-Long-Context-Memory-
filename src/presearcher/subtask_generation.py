import dspy

class SubtaskGenerationAgent(dspy.Signature):
    """A user is working on a complex research task and they want to break it down into a list of subtasks that,
    once answered, can be composed to answer the original research task.

    Given a research task:
    - Generate a list of subtasks that, once answered, can be composed to answer the original research task.
    - Generate an explanation for how to compose ONLY those subtasks, without relying on any other knowledge,
      to answer the original research task.

    CRITICAL REQUIREMENT - Each subtask MUST be phrased as a standalone, independent question:
    - DO NOT reference other subtasks (e.g., avoid "these indicators", "the countries mentioned above", "based on the previous")
    - Each question must be completely self-contained and researchable on its own
    - Include all necessary context directly within each subtask question

    Be explicit about:
    - How each subtask contributes to the final answer.
    - The order in which subtasks should be addressed (if relevant).
    - How to synthesize the subtask answers into a single coherent answer.

    Here's an example:

    Research Task:
        "What is the current state of AI in the healthcare industry?"

    Subtasks:
        1. What are the main current applications of AI in healthcare (e.g., diagnostics, imaging, triage,
           drug discovery, operations, patient monitoring, administrative tasks)?
        2. How widely are AI applications in healthcare (such as diagnostics, imaging, drug discovery, and administrative
           automation) adopted across different healthcare settings (e.g., large hospitals, clinics, telehealth providers,
           pharma), and what are the main adoption patterns and gaps?
        3. What evidence exists about the effectiveness and limitations of AI applications in healthcare
           (such as diagnostics, imaging, and drug discovery) compared to traditional approaches
           (e.g., accuracy vs clinicians, impact on workflow, patient outcomes, generalization issues)?
        4. What are the key barriers and risks affecting AI deployment in healthcare today
           (e.g., regulation, data quality and access, bias and fairness, interoperability, clinician trust, liability)?
        5. Who are the main types of actors driving AI in healthcare right now
           (e.g., big tech, startups, hospitals, payers, regulators) and what strategies or initiatives are they pursuing?
        6. What short-term trends (next 3–5 years) in AI healthcare applications, evidence-based outcomes, regulatory
           changes, and key industry actors are most likely to shape how AI is used in healthcare?

    Explanation for composing the subtasks to answer the research task:

        Step 1 – Describe where AI is used:
            Use Subtask 1 to enumerate the key application areas; this defines the scope of AI's presence in healthcare.

        Step 2 – Characterize how pervasive it is:
            Use Subtask 2 to explain how common each application is and in which settings, converting the use-case list
            into a picture of real-world penetration.

        Step 3 – Assess performance and real-world impact:
            Use Subtask 3 to qualify the above with evidence about effectiveness, limitations, and impact on workflows
            and outcomes, providing the quality dimension of the current state.

        Step 4 – Identify constraints and risks:
            Use Subtask 4 to explain why adoption looks the way it does by connecting barriers and risks to the
            applications and settings described in Subtasks 1–3, showing why the current state is limited or uneven.

        Step 5 – Map the ecosystem of actors:
            Use Subtask 5 to show who is shaping this landscape and how, linking each actor type to particular
            applications, deployment patterns, or barriers from Subtasks 1–4.

        Step 6 – Synthesize into a “current state” narrative:
            Combine insights from Subtasks 1–5 into a cohesive description of:
                - What AI does in healthcare today.
                - How common and mature these uses are.
                - How well they work and where they fall short.
                - What holds them back or introduces risk.
                - Who is driving or constraining change.

            This synthesis, using only information from those subtasks, answers:
                "What is the current state of AI in the healthcare industry?"

        Step 7 – Optional short-term outlook grounded only in the subtasks:
            Use Subtask 6 to project near-term trends strictly based on the current applications, evidence,
            barriers, and actors already described. This does not introduce new external knowledge; it repackages
            patterns from Subtasks 1–5 into a concise picture of where the current state is heading next.

    """

    research_task: str = dspy.InputField(
        description="The user's research task or query that needs to be decomposed into subtasks."
    )

    max_subtasks: int = dspy.InputField(
        description="The maximum number of subtasks to generate. Generate at most this many subtasks."
    )

    subtasks: list[str] = dspy.OutputField(
        description="A list of concrete subtasks. Each subtask MUST be phrased as a standalone, independent question "
                    "that can be researched completely on its own without any reference to other subtasks. "
                    "DO NOT use phrases like 'these indicators', 'the countries mentioned above', 'based on the previous', "
                    "or any other references to other subtasks. Each subtask should include all necessary context within "
                    "the question itself. Each subtask should be a specific, answerable question that contributes directly "
                    "to answering the original research_task. The list must contain at most max_subtasks items."
    )

    composition_explanation: str = dspy.OutputField(
        description="A step-by-step explanation of how to use ONLY the provided subtasks—without introducing "
                    "any additional subtasks or external knowledge—to synthesize a final answer to the original "
                    "research_task. Clearly describe how each subtask's answer participates in the final synthesis."
    )