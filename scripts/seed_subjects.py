# ============================================================================
# Seed Curriculum Data (ZIMSEC Complete)
# ============================================================================
"""
Script to seed subjects and topics into the database.
Includes Primary, O-Level, and A-Level subjects for ZIMSEC.

Usage:
    python scripts/seed_subjects.py
"""

import asyncio
import sys
import os

# Ensure the app directory is in the python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from app.models.curriculum import Subject, Topic
from sqlalchemy import select

# ZIMSEC Curriculum Data (Heritage-Based Curriculum 2024-2030)
CURRICULUM_DATA = {
    "primary": [
        {
            "name": "Mathematics (Junior)",
            "code": "ZIM-PRI-MAT",
            "topics": [
                {"name": "Number Concepts", "grades": ["Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Operations (Add/Sub/Mult/Div)", "grades": ["Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Fractions, Decimals and Percentages", "grades": ["Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Measures (Length, Mass, Time)", "grades": ["Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Financial Literacy", "grades": ["Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Data Handling", "grades": ["Grade 6", "Grade 7"]},
                {"name": "Geometry and Shapes", "grades": ["Grade 3", "Grade 4", "Grade 5"]},
            ]
        },
        {
            "name": "English Language",
            "code": "ZIM-PRI-ENG",
            "topics": [
                {"name": "Oral Communication", "grades": ["Grade 1", "Grade 2", "Grade 3", "Grade 4"]},
                {"name": "Reading Comprehension", "grades": ["Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Language Structures (Grammar)", "grades": ["Grade 4", "Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Creative Writing", "grades": ["Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Summary Writing", "grades": ["Grade 6", "Grade 7"]},
            ]
        },
        {
            "name": "Indigenous Language (Shona)",
            "code": "ZIM-PRI-SHO",
            "topics": [
                {"name": "Nzwisiso (Comprehension)", "grades": ["Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Rondedzero (Composition)", "grades": ["Grade 4", "Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Tsumo neMadimikira (Proverbs & Idioms)", "grades": ["Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Grammar (Zvirungamutauro)", "grades": ["Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7"]},
            ]
        },
        {
            "name": "Indigenous Language (Ndebele)",
            "code": "ZIM-PRI-NDE",
            "topics": [
                {"name": "Ukuzwisisa (Comprehension)", "grades": ["Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Indatshana (Composition)", "grades": ["Grade 4", "Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Izaga leZimo (Proverbs & Idioms)", "grades": ["Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Uhlelo (Grammar)", "grades": ["Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7"]},
            ]
        },
        {
            "name": "Science and Technology",
            "code": "ZIM-PRI-SCI",
            "topics": [
                {"name": "Living Things and Environment", "grades": ["Grade 4", "Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Materials and Matter", "grades": ["Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Energy and Fuels", "grades": ["Grade 6", "Grade 7"]},
                {"name": "ICT Tools", "grades": ["Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Structures and Mechanisms", "grades": ["Grade 5", "Grade 6", "Grade 7"]},
            ]
        },
        {
            "name": "Heritage and Social Studies",
            "code": "ZIM-PRI-HSS",
            "topics": [
                {"name": "Family and Community", "grades": ["Grade 3", "Grade 4"]},
                {"name": "National Symbols and Identity", "grades": ["Grade 3", "Grade 4", "Grade 5"]},
                {"name": "Zimbabwean Constitution", "grades": ["Grade 6", "Grade 7"]},
                {"name": "Natural Resources", "grades": ["Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Pre-colonial History", "grades": ["Grade 6", "Grade 7"]},
            ]
        },
        {
            "name": "Visual and Performing Arts",
            "code": "ZIM-PRI-VPA",
            "topics": [
                {"name": "Music and Dance", "grades": ["Grade 3", "Grade 4", "Grade 5"]},
                {"name": "Visual Arts (Drawing & Painting)", "grades": ["Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7"]},
                {"name": "Theatre and Drama", "grades": ["Grade 5", "Grade 6", "Grade 7"]},
            ]
        },
    ],
    "secondary": [
        # --- CORE SUBJECTS ---
        {
            "name": "Mathematics",
            "code": "4004",
            "topics": [
                {"name": "Number & Set Language", "grades": ["Form 1", "Form 2"]},
                {"name": "Consumer Arithmetic", "grades": ["Form 2", "Form 3"]},
                {"name": "Algebraic Manipulation", "grades": ["Form 1", "Form 2", "Form 3", "Form 4"]},
                {"name": "Plane Geometry & Loci", "grades": ["Form 2", "Form 3", "Form 4"]},
                {"name": "Mensuration (Area & Volume)", "grades": ["Form 3", "Form 4"]},
                {"name": "Trigonometry", "grades": ["Form 3", "Form 4"]},
                {"name": "Matrices & Transformations", "grades": ["Form 4"]},
                {"name": "Probability & Statistics", "grades": ["Form 3", "Form 4"]},
                {"name": "Vectors", "grades": ["Form 4"]},
            ]
        },
        {
            "name": "English Language",
            "code": "1122",
            "topics": [
                {"name": "Free Composition", "grades": ["Form 3", "Form 4"]},
                {"name": "Guided Composition", "grades": ["Form 3", "Form 4"]},
                {"name": "Reading Comprehension", "grades": ["Form 1", "Form 2", "Form 3", "Form 4"]},
                {"name": "Summary Writing", "grades": ["Form 3", "Form 4"]},
                {"name": "Register and Situational Writing", "grades": ["Form 3", "Form 4"]},
            ]
        },
        {
            "name": "Combined Science",
            "code": "4003",
            "topics": [
                {"name": "Biology: Cell Structure & Function", "grades": ["Form 1", "Form 2"]},
                {"name": "Biology: Human Nutrition & Digestion", "grades": ["Form 3", "Form 4"]},
                {"name": "Biology: Reproduction & Health", "grades": ["Form 3", "Form 4"]},
                {"name": "Chemistry: Matter & Periodic Table", "grades": ["Form 1", "Form 2"]},
                {"name": "Chemistry: Acids, Bases & Salts", "grades": ["Form 3"]},
                {"name": "Chemistry: Industrial Processes", "grades": ["Form 4"]},
                {"name": "Physics: Energy & Energy Resources", "grades": ["Form 2", "Form 3"]},
                {"name": "Physics: Electricity & Magnetism", "grades": ["Form 3", "Form 4"]},
                {"name": "Physics: Forces & Machines", "grades": ["Form 3", "Form 4"]},
            ]
        },
        {
            "name": "Heritage Studies",
            "code": "4006",
            "topics": [
                {"name": "Socialisation and Identity", "grades": ["Form 1", "Form 2"]},
                {"name": "Indigenous Knowledge Systems", "grades": ["Form 2", "Form 3"]},
                {"name": "National History and Sovereignty", "grades": ["Form 3", "Form 4"]},
                {"name": "The Constitution and Rights", "grades": ["Form 3", "Form 4"]},
            ]
        },
        
        # --- SCIENCES & TECH ---
        {
            "name": "Computer Science",
            "code": "4041",
            "topics": [
                {"name": "Hardware and Software", "grades": ["Form 1", "Form 2"]},
                {"name": "Data Representation (Binary/Hex)", "grades": ["Form 3", "Form 4"]},
                {"name": "Algorithm Design & Flowcharts", "grades": ["Form 3", "Form 4"]},
                {"name": "Programming (Python/VB)", "grades": ["Form 3", "Form 4"]},
                {"name": "Databases", "grades": ["Form 4"]},
                {"name": "Networks and Internet", "grades": ["Form 3", "Form 4"]},
                {"name": "Computer Security & Ethics", "grades": ["Form 4"]},
            ]
        },
        {
            "name": "Agriculture",
            "code": "5035",
            "topics": [
                {"name": "General Agriculture & Soil Science", "grades": ["Form 1", "Form 2"]},
                {"name": "Crop Husbandry (Maize/Tobacco/Cotton)", "grades": ["Form 3", "Form 4"]},
                {"name": "Livestock Husbandry (Cattle/Poultry)", "grades": ["Form 3", "Form 4"]},
                {"name": "Horticulture", "grades": ["Form 3", "Form 4"]},
                {"name": "Farm Engineering & Structures", "grades": ["Form 3", "Form 4"]},
                {"name": "Agro-Business", "grades": ["Form 4"]},
            ]
        },
        {
            "name": "Geography",
            "code": "4022",
            "topics": [
                {"name": "Map Reading & Interpretation", "grades": ["Form 1", "Form 2", "Form 3", "Form 4"]},
                {"name": "Physical Geography: Weather & Climate", "grades": ["Form 1", "Form 2"]},
                {"name": "Physical Geography: Plate Tectonics", "grades": ["Form 3", "Form 4"]},
                {"name": "Human Geography: Population", "grades": ["Form 3", "Form 4"]},
                {"name": "Economic Geography: Agriculture & Mining", "grades": ["Form 3", "Form 4"]},
                {"name": "Environmental Management", "grades": ["Form 3", "Form 4"]},
            ]
        },

        # --- COMMERCIALS ---
        {
            "name": "Commerce",
            "code": "7103",
            "topics": [
                {"name": "Production", "grades": ["Form 1", "Form 2"]},
                {"name": "Retail Trade", "grades": ["Form 2", "Form 3"]},
                {"name": "Wholesale Trade", "grades": ["Form 3"]},
                {"name": "Documents of Trade", "grades": ["Form 3", "Form 4"]},
                {"name": "Banking and Finance", "grades": ["Form 4"]},
                {"name": "International Trade", "grades": ["Form 4"]},
                {"name": "Insurance and Transport", "grades": ["Form 4"]},
            ]
        },
        {
            "name": "Principles of Accounts",
            "code": "7112",
            "topics": [
                {"name": "Double Entry Bookkeeping", "grades": ["Form 2", "Form 3"]},
                {"name": "Books of Original Entry", "grades": ["Form 3"]},
                {"name": "The Ledger and Trial Balance", "grades": ["Form 3"]},
                {"name": "Financial Statements (Sole Trader)", "grades": ["Form 3", "Form 4"]},
                {"name": "Partnership Accounts", "grades": ["Form 4"]},
                {"name": "Non-Profit Organisations", "grades": ["Form 4"]},
            ]
        },

        # --- ARTS & HUMANITIES ---
        {
            "name": "History",
            "code": "2167",
            "topics": [
                {"name": "Great Zimbabwe State", "grades": ["Form 1", "Form 2"]},
                {"name": "The Mutapa & Rozvi States", "grades": ["Form 2", "Form 3"]},
                {"name": "The Ndebele State", "grades": ["Form 3"]},
                {"name": "Colonisation & The First Chimurenga", "grades": ["Form 3", "Form 4"]},
                {"name": "The Second Chimurenga & Independence", "grades": ["Form 4"]},
                {"name": "World Affairs (WWI & WWII)", "grades": ["Form 4"]},
            ]
        },
        {
            "name": "Family and Religious Studies (FRS)",
            "code": "4047",
            "topics": [
                {"name": "Indigenous Religion: Concept of God", "grades": ["Form 3", "Form 4"]},
                {"name": "Indigenous Religion: Spirits & Rituals", "grades": ["Form 3", "Form 4"]},
                {"name": "Judaism: Prophecy", "grades": ["Form 3", "Form 4"]},
                {"name": "Christianity: Life and Ministry of Jesus", "grades": ["Form 3", "Form 4"]},
                {"name": "Christianity: Death and Resurrection", "grades": ["Form 4"]},
            ]
        },
        {
            "name": "Literature in English",
            "code": "2011",
            "topics": [
                {"name": "Zimbabwean Prose", "grades": ["Form 3", "Form 4"]},
                {"name": "African Prose", "grades": ["Form 3", "Form 4"]},
                {"name": "Shakespearean Drama", "grades": ["Form 3", "Form 4"]},
                {"name": "Poetry Appreciation", "grades": ["Form 3", "Form 4"]},
            ]
        },
        {
            "name": "Shona",
            "code": "3159",
            "topics": [
                {"name": "Rondedzero (Composition)", "grades": ["Form 3", "Form 4"]},
                {"name": "Nzwisiso (Comprehension)", "grades": ["Form 3", "Form 4"]},
                {"name": "Ukama (Relationships/Culture)", "grades": ["Form 3", "Form 4"]},
                {"name": "Literature (Novels & Poetry)", "grades": ["Form 3", "Form 4"]},
            ]
        },
        {
            "name": "Ndebele",
            "code": "3155",
            "topics": [
                {"name": "Indatshana (Composition)", "grades": ["Form 3", "Form 4"]},
                {"name": "Ukuzwisisa (Comprehension)", "grades": ["Form 3", "Form 4"]},
                {"name": "Amasiko (Culture)", "grades": ["Form 3", "Form 4"]},
                {"name": "Literature (Novels & Poetry)", "grades": ["Form 3", "Form 4"]},
            ]
        }
    ],
    "a_level": [
        # --- SCIENCES ---
        {
            "name": "Computer Science",
            "code": "9196",
            "topics": [
                {"name": "System Analysis and Design", "grades": ["Lower 6", "Upper 6"]},
                {"name": "Data Representation & Structures", "grades": ["Lower 6"]},
                {"name": "Algorithms and Programming", "grades": ["Lower 6", "Upper 6"]},
                {"name": "Computer Architecture", "grades": ["Lower 6"]},
                {"name": "Databases and Normalisation", "grades": ["Upper 6"]},
                {"name": "Networking and Communication", "grades": ["Upper 6"]},
            ]
        },
        {
            "name": "Pure Mathematics",
            "code": "9164",
            "topics": [
                {"name": "Algebra & Quadratics", "grades": ["Lower 6"]},
                {"name": "Co-ordinate Geometry", "grades": ["Lower 6"]},
                {"name": "Calculus: Differentiation", "grades": ["Lower 6", "Upper 6"]},
                {"name": "Calculus: Integration", "grades": ["Lower 6", "Upper 6"]},
                {"name": "Vectors and Complex Numbers", "grades": ["Upper 6"]},
                {"name": "Differential Equations", "grades": ["Upper 6"]},
                {"name": "Probability & Statistics (Mech)", "grades": ["Lower 6", "Upper 6"]},
            ]
        },
        {
            "name": "Physics",
            "code": "9188",
            "topics": [
                {"name": "Mechanics", "grades": ["Lower 6"]},
                {"name": "Matter and Phases", "grades": ["Lower 6"]},
                {"name": "Oscillations and Waves", "grades": ["Lower 6", "Upper 6"]},
                {"name": "Electricity and Magnetism", "grades": ["Lower 6", "Upper 6"]},
                {"name": "Nuclear and Quantum Physics", "grades": ["Upper 6"]},
            ]
        },
        {
            "name": "Chemistry",
            "code": "9189",
            "topics": [
                {"name": "Atoms, Molecules and Stoichiometry", "grades": ["Lower 6"]},
                {"name": "Chemical Bonding", "grades": ["Lower 6"]},
                {"name": "Chemical Energetics", "grades": ["Lower 6", "Upper 6"]},
                {"name": "Electrochemistry", "grades": ["Upper 6"]},
                {"name": "Equilibria", "grades": ["Upper 6"]},
                {"name": "Organic Chemistry", "grades": ["Lower 6", "Upper 6"]},
            ]
        },
        {
            "name": "Biology",
            "code": "9190",
            "topics": [
                {"name": "Cell Structure & Microscopy", "grades": ["Lower 6"]},
                {"name": "Biological Molecules & Enzymes", "grades": ["Lower 6"]},
                {"name": "Cell Membranes & Transport", "grades": ["Lower 6"]},
                {"name": "Genetic Control (DNA/RNA)", "grades": ["Upper 6"]},
                {"name": "Energy and Respiration", "grades": ["Upper 6"]},
                {"name": "Photosynthesis", "grades": ["Upper 6"]},
            ]
        },
        {
            "name": "Crop Science",
            "code": "9195",
            "topics": [
                {"name": "Plant Physiology", "grades": ["Lower 6"]},
                {"name": "Soil Science", "grades": ["Lower 6"]},
                {"name": "Crop Protection (Pests/Diseases)", "grades": ["Upper 6"]},
                {"name": "Genetics and Plant Breeding", "grades": ["Upper 6"]},
            ]
        },

        # --- COMMERCIALS ---
        {
            "name": "Economics",
            "code": "9158",
            "topics": [
                {"name": "Basic Economic Problem (Scarcity)", "grades": ["Lower 6"]},
                {"name": "Price Mechanism (Demand & Supply)", "grades": ["Lower 6"]},
                {"name": "Market Failure & Intervention", "grades": ["Lower 6"]},
                {"name": "Macroeconomics (Inflation/Unemployment)", "grades": ["Upper 6"]},
                {"name": "International Trade & Exchange Rates", "grades": ["Upper 6"]},
            ]
        },
        {
            "name": "Business Studies",
            "code": "9198",
            "topics": [
                {"name": "Business and its Environment", "grades": ["Lower 6"]},
                {"name": "People in Organisations (HR)", "grades": ["Lower 6", "Upper 6"]},
                {"name": "Marketing Management", "grades": ["Lower 6", "Upper 6"]},
                {"name": "Operations Management", "grades": ["Upper 6"]},
                {"name": "Finance and Accounting", "grades": ["Upper 6"]},
            ]
        },
        {
            "name": "Accounting",
            "code": "9197",
            "topics": [
                {"name": "Financial Accounting (Sole Trader)", "grades": ["Lower 6"]},
                {"name": "Partnership & Company Accounts", "grades": ["Lower 6", "Upper 6"]},
                {"name": "Cost and Management Accounting", "grades": ["Lower 6", "Upper 6"]},
                {"name": "Manufacturing Accounts", "grades": ["Upper 6"]},
            ]
        },

        # --- ARTS ---
        {
            "name": "Geography",
            "code": "9156",
            "topics": [
                {"name": "Hydrology and Fluvial Geomorphology", "grades": ["Lower 6"]},
                {"name": "Atmosphere and Weather", "grades": ["Lower 6"]},
                {"name": "Rocks and Weathering", "grades": ["Lower 6"]},
                {"name": "Population and Migration", "grades": ["Upper 6"]},
                {"name": "Settlement Dynamics", "grades": ["Upper 6"]},
            ]
        },
        {
            "name": "History",
            "code": "9155",
            "topics": [
                {"name": "European History (1789-1964)", "grades": ["Lower 6", "Upper 6"]},
                {"name": "History of Zimbabwe", "grades": ["Lower 6", "Upper 6"]},
                {"name": "Regional & International Affairs", "grades": ["Upper 6"]},
                {"name": "Tropical Africa", "grades": ["Lower 6"]},
            ]
        },
        {
            "name": "Literature in English",
            "code": "9153",
            "topics": [
                {"name": "Shakespearean Drama", "grades": ["Lower 6", "Upper 6"]},
                {"name": "Modern Drama", "grades": ["Lower 6", "Upper 6"]},
                {"name": "Poetry", "grades": ["Lower 6", "Upper 6"]},
                {"name": "Prose (African & International)", "grades": ["Lower 6", "Upper 6"]},
            ]
        },
        {
            "name": "Sociology",
            "code": "9061",
            "topics": [
                {"name": "Socialisation, Culture and Identity", "grades": ["Lower 6"]},
                {"name": "Family and Households", "grades": ["Lower 6"]},
                {"name": "Education", "grades": ["Lower 6"]},
                {"name": "Religion", "grades": ["Upper 6"]},
                {"name": "Crime and Deviance", "grades": ["Upper 6"]},
                {"name": "Theory and Methods", "grades": ["Upper 6"]},
            ]
        },
        {
            "name": "Divinity",
            "code": "9154",
            "topics": [
                {"name": "Old Testament Prophets", "grades": ["Lower 6", "Upper 6"]},
                {"name": "The Four Gospels", "grades": ["Lower 6", "Upper 6"]},
                {"name": "The Apostolic Age", "grades": ["Lower 6", "Upper 6"]},
            ]
        },
    ]
}

async def seed_curriculum():
    """Seed the curriculum data"""
    async with async_session_maker() as db:
        print("Starting curriculum seeding...")
        
        for level, subjects in CURRICULUM_DATA.items():
            print(f"\n--- Seeding {level.upper().replace('_', ' ')} Subjects ---")
            
            for subject_data in subjects:
                # Check if subject exists by code (codes are unique)
                result = await db.execute(
                    select(Subject).where(Subject.code == subject_data["code"])
                )
                existing_subject = result.scalar_one_or_none()
                
                if existing_subject:
                    print(f"  [SKIP] Subject '{subject_data['name']}' ({subject_data['code']}) exists.")
                    subject = existing_subject
                else:
                    subject = Subject(
                        name=subject_data["name"],
                        code=subject_data["code"],
                        education_level=level,
                        description=f"{subject_data['name']} syllabus for {level.replace('_', ' ').title()}"
                    )
                    db.add(subject)
                    await db.flush() # Flush to get the ID
                    print(f"  [CREATE] Subject '{subject_data['name']}' ({subject_data['code']}) created.")
                
                # Add topics
                topics_added = 0
                for idx, topic_data in enumerate(subject_data.get("topics", [])):
                    for grade in topic_data.get("grades", []):
                        # Check if topic exists for this subject and grade
                        result = await db.execute(
                            select(Topic)
                            .where(Topic.subject_id == subject.id)
                            .where(Topic.name == topic_data["name"])
                            .where(Topic.grade == grade)
                        )
                        existing_topic = result.scalar_one_or_none()
                        
                        if not existing_topic:
                            topic = Topic(
                                subject_id=subject.id,
                                name=topic_data["name"],
                                grade=grade,
                                order_index=idx,
                                description=f"{topic_data['name']} topic for {grade}"
                            )
                            db.add(topic)
                            topics_added += 1
                
                if topics_added > 0:
                    print(f"    + Added {topics_added} topics to {subject.name}")

        await db.commit()
        print("\nCurriculum seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_curriculum())