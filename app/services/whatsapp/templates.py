# ============================================================================
# WhatsApp Message Templates
# ============================================================================
"""WhatsApp message templates for various scenarios"""

class WhatsAppTemplates:
    """Pre-defined message templates for WhatsApp"""
    
    # Welcome Messages
    WELCOME_NEW_USER = """🎓 *Welcome to Zim Student Companion!*

I'm your AI study buddy for ZIMSEC exams. I'll help you:
📚 Practice with real exam questions
🎯 Understand difficult topics
🏆 Compete with other students
📊 Track your progress

Let's get you set up! Are you a:
1️⃣ Student
2️⃣ Parent
3️⃣ Teacher"""

    WELCOME_BACK = """👋 Welcome back, {name}!

🔥 Your streak: {streak} days
📊 Level {level} ({title})
💎 {xp} XP

Ready to learn? Type *practice* or ask me anything!"""

    # Practice Messages
    PRACTICE_START = """📚 *Starting Practice Session*

Subject: {subject}
Questions: {num_questions}
Difficulty: {difficulty}

Let's go! 🚀

Type 'quit' anytime to end the session.
Type 'hint' if you need help.
Type 'skip' to try another question."""

    PRACTICE_QUESTION = """📝 *Question {current}/{total}* {difficulty_emoji}

{question}

{options}

💡 Reply with your answer, or:
• Type "hint" for a clue
• Type "skip" to try another
• Type "quit" to end session"""

    CORRECT_ANSWER = """{emoji} *Correct!* {name}, great job! 🌟

{feedback}

+{xp} XP earned!

{progress}"""

    INCORRECT_ANSWER = """❌ Not quite right.

{feedback}

📖 The correct answer: {correct_answer}

Don't worry, learning from mistakes is how we improve! 💪

{progress}"""

    PRACTICE_COMPLETE = """🎉 *Session Complete!*

📊 *Your Results:*
━━━━━━━━━━━━━━━
✅ Correct: {correct}/{total}
📈 Score: {score}%
🎯 XP Earned: +{xp}
⏱️ Time: {time}

{message}

Type *practice* for another session!
Type *progress* to see your stats."""

    # Hint Messages
    HINT_MESSAGE = """💡 *Hint {number}/3:*

{hint}

Think about it and try again! 🤔"""

    NO_MORE_HINTS = """⚠️ No more hints available!

You've used all 3 hints. Give it your best shot, or type 'skip' to try another question."""

    # Parent Messages
    PARENT_LINK_REQUEST = """👨‍👩‍👧 *Parent Link Request*

To monitor your child's progress, you'll need their 6-digit parent code.

Ask your child to type "parent code" in their chat to get the code.

Once you have it, send it here!"""

    PARENT_LINKED = """✅ *Successfully Linked!*

You're now connected to {child_name}'s account.

You'll receive:
📊 Weekly progress reports
🏆 Achievement notifications
📈 Performance insights

Type *report* anytime to see current progress."""

    PARENT_WEEKLY_REPORT = """📊 *Weekly Report for {child_name}*

📅 {week_range}

📈 *Summary:*
• Questions: {questions}
• Accuracy: {accuracy}%
• Active Days: {active_days}/7
• Streak: {streak} days 🔥

💪 Strongest: {strongest}
📚 Needs Practice: {weakest}

{recommendations}"""

    # Achievement Messages
    ACHIEVEMENT_UNLOCKED = """🏆 *ACHIEVEMENT UNLOCKED!*

{icon} *{name}*

{description}

+{points} XP earned!

Keep up the amazing work! 🌟"""

    LEVEL_UP = """⬆️ *LEVEL UP!*

You've reached *Level {level}*!

🎖️ New Title: {title}

You're making incredible progress! Keep it up! 🚀"""

    # Streak Messages
    STREAK_WARNING = """⚠️ *Streak Alert!*

Your {streak}-day streak is at risk! 🔥

You haven't practiced today yet. Just answer ONE question to keep your streak alive!

Type *practice* now - it only takes 2 minutes!"""

    STREAK_LOST = """😢 *Streak Lost*

Your {old_streak}-day streak has ended.

But don't give up! Start building a new one today.

Type *practice* to begin! 💪"""

    STREAK_MILESTONE = """🔥 *Streak Milestone!*

Amazing! You've reached a *{streak}-day streak*!

That's {streak} days of consistent learning!

+{bonus_xp} bonus XP earned! 🎉"""

    # Competition Messages
    COMPETITION_ANNOUNCEMENT = """🏆 *New Competition!*

"{name}"

📅 {start} - {end}
📝 {questions} questions
⏱️ {time_limit} minutes
🎁 Prizes: {prizes}

Type *join {id}* to register!"""

    COMPETITION_REMINDER = """⏰ *Competition Starting Soon!*

"{name}" begins in {time_remaining}!

Make sure you're ready. Good luck! 🍀"""

    COMPETITION_RESULT = """🏁 *Competition Results*

"{name}"

Your Rank: #{rank} out of {total}
Score: {score}
Time: {time}

{prize_message}

{leaderboard_preview}"""

    # Subscription Messages
    SUBSCRIPTION_EXPIRING = """⏰ *Subscription Alert*

Your {tier} subscription expires in {days} day(s)!

Renew now to keep:
✅ Unlimited questions
✅ All subjects
✅ Past papers
✅ Parent reports

Type *renew* to extend your subscription."""

    SUBSCRIPTION_EXPIRED = """😢 *Subscription Expired*

Your {tier} subscription has ended.

You're now on the Free plan with limited features.

Type *upgrade* to see plans and continue unlimited learning!"""

    PAYMENT_SUCCESS = """✅ *Payment Successful!*

Your {plan} subscription is now active!

📅 Valid until: {expiry}
💎 Tier: {tier}

Enjoy unlimited learning! Type *menu* to get started."""

    # Help Messages
    HELP_MENU = """❓ *Help & Commands*

📚 *Learning:*
• *practice* - Start a practice session
• *ask [question]* - Ask any question
• *subjects* - Change your subjects

📊 *Progress:*
• *progress* - View your stats
• *achievements* - See your badges
• *leaderboard* - See rankings

👨‍👩‍👧 *Parents:*
• *parent code* - Get code to link parent
• *report* - View your report

💎 *Account:*
• *upgrade* - See subscription plans
• *settings* - Update your profile
• *help* - Show this menu

Just type a command or ask me anything!"""

    ERROR_MESSAGE = """😕 *Oops!*

Something went wrong. Please try again.

If the problem continues, type *help* for assistance.

Error: {error}"""

    @classmethod
    def format(cls, template_name: str, **kwargs) -> str:
        """Format a template with provided values"""
        template = getattr(cls, template_name, None)
        if template:
            try:
                return template.format(**kwargs)
            except KeyError as e:
                return template  # Return unformatted if missing keys
        return f"Template '{template_name}' not found"