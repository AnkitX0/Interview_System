from backend.database import SessionLocal
import backend.models as models

db = SessionLocal()

hr_questions = [
("Tell me about yourself.", "HR", "easy", "general"),
("Why do you want to work in this field?", "HR", "easy", "general"),
("What are your greatest strengths?", "HR", "easy", "general"),
("What is your biggest weakness?", "HR", "easy", "general"),
("Why should we hire you?", "HR", "easy", "general"),
("Where do you see yourself in five years?", "HR", "easy", "general"),
("What motivates you to work hard?", "HR", "easy", "general"),
("How do you handle stress or pressure?", "HR", "easy", "general"),
("What type of work environment do you prefer?", "HR", "easy", "general"),
("What are your career goals?", "HR", "easy", "general"),
("Tell me about a time you worked under pressure.", "HR", "easy", "general"),
("What do you know about our company?", "HR", "easy", "general"),
("Why did you choose your major?", "HR", "easy", "general"),
("What makes you unique compared to other candidates?", "HR", "easy", "general"),
("How do you prioritize tasks when you have multiple deadlines?", "HR", "easy", "general"),
("Tell me about your ideal manager.", "HR", "easy", "general"),
("What skills are you currently improving?", "HR", "easy", "general"),
("Describe yourself in three words.", "HR", "easy", "general"),
("What does success mean to you?", "HR", "easy", "general"),
("What do you expect from your first job?", "HR", "easy", "general"),
]

behavioral_questions = [
("Describe a challenging project you worked on.", "Behavioral", "medium", "general"),
("Tell me about a time you failed.", "Behavioral", "medium", "general"),
("Describe a time you solved a difficult problem.", "Behavioral", "medium", "general"),
("Tell me about a time you worked in a team.", "Behavioral", "medium", "general"),
("Describe a conflict you had with a teammate.", "Behavioral", "medium", "general"),
("Tell me about a time you had a tight deadline.", "Behavioral", "medium", "general"),
("Describe a time when you had to learn something quickly.", "Behavioral", "medium", "general"),
("Tell me about a situation where you showed leadership.", "Behavioral", "medium", "general"),
("Describe a time you had to adapt to change.", "Behavioral", "medium", "general"),
("Tell me about a time you made a mistake.", "Behavioral", "medium", "general"),
("Describe a time you handled criticism.", "Behavioral", "medium", "general"),
("Tell me about a time you helped a teammate.", "Behavioral", "medium", "general"),
("Describe a time you solved a conflict.", "Behavioral", "medium", "general"),
("Tell me about a time you improved a process.", "Behavioral", "medium", "general"),
("Describe a time you had to make a difficult decision.", "Behavioral", "medium", "general"),
("Tell me about a time you exceeded expectations.", "Behavioral", "medium", "general"),
("Describe a time you managed multiple tasks.", "Behavioral", "medium", "general"),
("Tell me about a time you took initiative.", "Behavioral", "medium", "general"),
("Describe a time you faced a major obstacle.", "Behavioral", "medium", "general"),
("Tell me about a time you had to persuade someone.", "Behavioral", "medium", "general"),
]

technical_questions = [
("Explain REST API architecture.", "Technical", "medium", "backend"),
("What is the difference between a process and a thread?", "Technical", "medium", "backend"),
("Explain how a hash table works.", "Technical", "medium", "backend"),
("What is time complexity?", "Technical", "easy", "backend"),
("Explain object-oriented programming.", "Technical", "easy", "backend"),
("What is the difference between SQL and NoSQL databases?", "Technical", "medium", "backend"),
("What is normalization in databases?", "Technical", "medium", "backend"),
("Explain indexing in databases.", "Technical", "medium", "backend"),
("What are ACID properties?", "Technical", "medium", "backend"),
("What is caching and why is it important?", "Technical", "medium", "backend"),
("Explain the MVC architecture.", "Technical", "medium", "backend"),
("What is a microservices architecture?", "Technical", "hard", "backend"),
("Explain the difference between synchronous and asynchronous programming.", "Technical", "medium", "backend"),
("What is dependency injection?", "Technical", "medium", "backend"),
("Explain the concept of middleware.", "Technical", "medium", "backend"),
("What is Docker and why is it used?", "Technical", "medium", "backend"),
("Explain load balancing.", "Technical", "medium", "backend"),
("What is rate limiting?", "Technical", "medium", "backend"),
("Explain how authentication works in web applications.", "Technical", "medium", "backend"),
("What is JWT authentication?", "Technical", "medium", "backend"),
("Explain the CAP theorem.", "Technical", "hard", "backend"),
("What is eventual consistency?", "Technical", "hard", "backend"),
("Explain message queues.", "Technical", "medium", "backend"),
("What is API versioning?", "Technical", "medium", "backend"),
("Explain horizontal vs vertical scaling.", "Technical", "medium", "backend"),
]

pressure_questions = [
("Your project failed in production. What do you do?", "Pressure", "hard", "general"),
("A teammate is underperforming. How do you handle it?", "Pressure", "hard", "general"),
("Why should we hire you instead of someone better?", "Pressure", "hard", "general"),
("Convince me you deserve this job.", "Pressure", "hard", "general"),
("Your manager gives unrealistic deadlines. What do you do?", "Pressure", "hard", "general"),
("What would you do if you disagreed with your manager?", "Pressure", "hard", "general"),
("How do you respond to harsh criticism?", "Pressure", "hard", "general"),
("What would you do if your project suddenly failed before release?", "Pressure", "hard", "general"),
("How would you handle working with a difficult teammate?", "Pressure", "hard", "general"),
("What would you do if you realized you made a serious mistake?", "Pressure", "hard", "general"),
("How do you deal with failure?", "Pressure", "hard", "general"),
("What if you don't know the answer to a question?", "Pressure", "hard", "general"),
("How would you convince a skeptical interviewer?", "Pressure", "hard", "general"),
("Explain why you deserve this role.", "Pressure", "hard", "general"),
("What if you fail your first major project?", "Pressure", "hard", "general"),
]

all_questions = hr_questions + behavioral_questions + technical_questions + pressure_questions

if db.query(models.QuestionBank).count() > 0:
    print("Questions already exist. Seeder skipped.")
    exit()
    
for q in all_questions:
    db.add(
    models.QuestionBank(
            question_text=q[0],
            category=q[1],
            difficulty=q[2],
            role=q[3]
        )
    )

db.commit()

print("80 questions inserted successfully.")