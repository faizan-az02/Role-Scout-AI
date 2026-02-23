from crewai import Task, Crew
from agents.researcher import create_researcher

researcher = create_researcher()

task = Task(
    description=(
        "Generate 3 smart search queries to find the CEO of Meta. "
        "Include designation aliases."
    ),
    expected_output="A list of 3 optimized search queries.",
    agent=researcher
)

crew = Crew(
    agents=[researcher],
    tasks=[task],
    verbose=True
)

result = crew.kickoff()
print("\nFINAL OUTPUT:\n", result)