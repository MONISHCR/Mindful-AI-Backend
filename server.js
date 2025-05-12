// Required Modules
const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
const { body, validationResult } = require("express-validator");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const axios = require("axios");
require("dotenv").config();

// Import Models
const User = require("./models/User");
const Journal = require("./models/Journal");
const QuizResult = require("./models/QuizResult");
const Mood = require("./models/Mood");
// const { default: ArtTherapy } = require("../PSYCHOLOGICAL-CHATBOT-main/src/components/ArtTherapy");

const app = express();
const PORT = process.env.PORT || 3001;
const JWT_SECRET = process.env.JWT_SECRET || "your_secret_key"; // Ensure this is the same everywhere

// Middleware
app.use(express.json());
app.use(cors({
  origin: 'http://localhost:3000', // React app's URL
  methods: ['GET', 'POST', 'PUT', 'DELETE'], // Allowed methods
  allowedHeaders: ['Content-Type', 'Authorization'] // Allowed headers
  
}));

const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];  // Extract token from 'Bearer <token>'
  if (!token) return res.sendStatus(401);  // No token provided

  jwt.verify(token, JWT_SECRET, (err, user) => {  // Replace with your secret key
    if (err) return res.sendStatus(403);  // Token verification failed
    req.user = user;  // Attach the decoded user to the request object
    next();  // Proceed to the next middleware/route handler
  });
};


// Connect to MongoDB
mongoose.connect(process.env.MONGO_URI, {
  useNewUrlParser: true,
  useUnifiedTopology: true,
})
.then(() => console.log("Mongodb connected"))
.catch((err) => console.log("MongoDB connection error:", err));

const db = mongoose.connection;
db.on("error", console.error.bind(console, "MongoDB connection error:"));
db.once("open", () => console.log("Connected to MongoDB"));

// Register Route
app.post(
  "/signup",
  [
    body("username").notEmpty().withMessage("Username is required"),
    body("email").isEmail().withMessage("Valid email is required"),
    body("password")
      .isLength({ min: 5 })
      .withMessage("Password must be at least 5 characters long"),
  ],
  async (req, res) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }

    const { username, email, password } = req.body;

    try {
      const existingUser = await User.findOne({
        $or: [{ username }, { email }],
      });

      if (existingUser) {
        return res
          .status(400)
          .json({ error: "Username or email already exists" });
      }

      const hashedPassword = await bcrypt.hash(password, 10);
      const newUser = new User({
        username,
        email,
        password: hashedPassword,
      });

      await newUser.save();
      res.status(201).json({ message: "User registered successfully" });
    } catch (error) {
      console.error("Error in /signup:", error);
      res.status(500).json({ error: "Server error" });
    }
  }
);

// Login Route
app.post("/login", async (req, res) => {
  const { username, password } = req.body;
  try {
    const user = await User.findOne({ username });
    if (!user) {
      return res.status(400).json({ error: "Invalid credentials" });
    }

    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) {
      return res.status(400).json({ error: "Invalid credentials" });
    }

    const token = jwt.sign({ userId: user._id }, JWT_SECRET, { expiresIn: "24h" });

    // ✅ Include userId in the response
    res.json({ token, userId: user._id });
  } catch (error) {
    console.error("Error in /login:", error);
    res.status(500).json({ error: "Server error" });
  }
});


// Middleware to check token
const auth = (req, res, next) => {
  const authHeader = req.header("Authorization");
  const token = authHeader && authHeader.split(" ")[1];

  if (!token) {
    console.error("No token provided");
    return res.status(401).json({ error: "No token provided" });
  }

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    console.error("JWT Verification Error:", error);
    res.status(401).json({ error: "Invalid token" });
  }
};

// Create Journal Entry (Protected)
// app.post("/journal", auth, async (req, res) => {
//   try {
//     const { content } = req.body;
//     const newEntry = new Journal({ content, userId: req.user.userId });
//     await newEntry.save();
//     res.status(201).json({ message: "Journal entry saved successfully" });
//   } catch (error) {
//     console.error("Error in /journal POST:", error);
//     res.status(500).json({ error: "Failed to save journal entry" });
//   }
// });

app.post("/journal", auth, async (req, res) => {
  try {
    const { content } = req.body;
    const analysisResponse = await axios.post("http://127.0.0.1:3002/analyze", { content });
    const { score, explanation, recommendation } = analysisResponse.data;
    const newEntry = new Journal({ 
      content, 
      userId: req.user.userId, 
      score, 
      explanation, 
      recommendation 
    });

    await newEntry.save();
    res.status(201).json({ message: "Journal entry saved successfully", score, explanation, recommendation });

  } catch (error) {
    console.error("Error in /journal POST:", error);
    res.status(500).json({ error: "Failed to save journal entry" });
  }
});

// Get User's Journal Entries (Protected)
app.get("/journal", auth, async (req, res) => {
  try {
    console.log("Authenticated User ID:", req.user.userId);
    const entries = await Journal.find({ userId: req.user.userId }).sort({ timestamp: -1 });
    res.json(entries);
  } catch (error) {
    console.error("Error in /journal GET:", error);
    res.status(500).json({ error: "Failed to fetch journal entries" });
  }
});

app.delete("/journal/:id", authenticateToken, async (req, res) => {
  try {
    const entryId = req.params.id;
    const entry = await Journal.findById(entryId);

    if (!entry) {
      return res.status(404).json({ message: "Journal entry not found" });
    }

    if (entry.userId.toString() !== req.user.userId) {
      return res.status(403).json({ message: "Not authorized to delete this entry" });
    }

    await Journal.findByIdAndDelete(entryId);
    res.status(200).json({ message: "Journal entry deleted successfully" });
  } catch (error) {
    console.error("Error deleting journal entry:", error);
    res.status(500).json({ message: "Server error" });
  }
});

// Sample quizzes
const quizzes = [
  {
    id: 1,
    title: "How stressed are you?",
    questions: [
      {
        question: "How often do you feel overwhelmed?",
        options: ["Rarely", "Sometimes", "Often", "All the time"],
        scores: [1, 2, 3, 4]
      },
      {
        question: "Do you struggle with sleep?",
        options: ["No", "Occasionally", "Frequently", "Always"],
        scores: [1, 2, 3, 4]
      },
      {
        question: "How often do you feel you have too much to do?",
        options: ["Rarely", "Sometimes", "Often", "Constantly"],
        scores: [1, 2, 3, 4]
      },
      {
        question: "Do you experience physical symptoms like headaches or tension?",
        options: ["Never", "Occasionally", "Often", "Very Often"],
        scores: [1, 2, 3, 4]
      },
      {
        question: "How easy is it for you to relax after a busy day?",
        options: ["Very easy", "Somewhat easy", "Difficult", "Almost impossible"],
        scores: [1, 2, 3, 4]
      }
    ],
    resultText: [
      "You're doing great!",
      "Mild stress detected.",
      "You seem stressed.",
      "High stress levels – consider help."
    ]
  },
  {
    id: 2,
    title: "Are you feeling anxious?",
    questions: [
      {
        question: "Do you worry about the future?",
        options: ["Not at all", "A little", "Often", "All the time"],
        scores: [1, 2, 3, 4]
      },
      {
        question: "How often do you experience restlessness?",
        options: ["Rarely", "Sometimes", "Frequently", "Constantly"],
        scores: [1, 2, 3, 4]
      },
      {
        question: "Do you have trouble concentrating due to worry?",
        options: ["Never", "Sometimes", "Often", "Always"],
        scores: [1, 2, 3, 4]
      },
      {
        question: "Do you feel tense or on edge frequently?",
        options: ["No", "Occasionally", "Most days", "Almost every day"],
        scores: [1, 2, 3, 4]
      },
      {
        question: "How often do you feel your heart racing without physical exertion?",
        options: ["Never", "Rarely", "Often", "Very often"],
        scores: [1, 2, 3, 4]
      }
    ],
    resultText: [
      "Calm and collected!",
      "Slight anxiety signs.",
      "Noticeable anxiety.",
      "High anxiety – consider support."
    ]
  },
  {
    id: 3,
    title: 'Student Stress and Focus Quiz',
    questions: [
      {
        question: 'How often do you feel overwhelmed with assignments?',
        options: ['Never', 'Rarely', 'Often', 'Always'],
        scores: [1, 2, 3, 4]
      },
      {
        question: 'How many hours do you sleep on average during the semester?',
        options: ['Less than 4', '4-6', '6-8', 'More than 8'],
        scores: [1, 2, 3, 4]
      },
      {
        question: 'Do you find it easy to focus during online classes?',
        options: ['Always', 'Most times', 'Sometimes', 'Never'],
        scores: [4, 3, 2, 1]
      },
      {
        question: 'How often do you feel motivated to study?',
        options: ['Always', 'Most times', 'Sometimes', 'Rarely'],
        scores: [4, 3, 2, 1]
      },
      {
        question: 'How would you describe your current mental state?',
        options: ['Focused and calm', 'Anxious but managing', 'Stressed', 'Burnt out'],
        scores: [4, 3, 2, 1]
      }
    ],
    resultText: [
      "You're focused and doing well!",
      "Some signs of academic stress.",
      "You seem to be struggling.",
      "You're burnt out - time to talk to someone."
    ]
  }
];

// Endpoint to get a random quiz
app.get('/quiz', (req, res) => {
  const randomIndex = Math.floor(Math.random() * quizzes.length);
  res.json(quizzes[randomIndex]);
});

// Endpoint to submit answers and get result
// app.post('/quiz/submit', auth, async (req, res) => {
//   const { quizId, answers } = req.body;
//   const quiz = quizzes.find(q => q.id === quizId);
//   if (!quiz) return res.status(404).json({ error: 'Quiz not found' });

//   if (!answers || !Array.isArray(answers)) {
//     return res.status(400).json({ error: 'Answers must be an array' });
//   }

//   // Count only the answered questions
//   let totalScore = 0;
//   let answeredCount = 0;

//   for (let i = 0; i < answers.length; i++) {
//     const val = answers[i];
//     if (val !== null && val !== undefined) {
//       totalScore += val;
//       answeredCount++;
//     }
//   }

//   if (answeredCount === 0) {
//     return res.status(400).json({ error: "You must answer at least one question." });
//   }

//   const maxScore = answeredCount * 4;
//   const percentage = totalScore / maxScore;

//   let resultText;
//   if (percentage <= 0.25) resultText = quiz.resultText[0];
//   else if (percentage <= 0.5) resultText = quiz.resultText[1];
//   else if (percentage <= 0.75) resultText = quiz.resultText[2];
//   else resultText = quiz.resultText[3];

//   try {
//     const newResult = new QuizResult({
//       userId: req.user.userId,
//       quizId,
//       answers,
//       totalScore,
//       percentage,
//       resultText,
//     });

//     await newResult.save();

//     res.json({ result: resultText, totalScore, percentage });
//   } catch (error) {
//     console.error("Error saving quiz result:", error);
//     res.status(500).json({ error: "Failed to save quiz result" });
//   }
// });

app.post('/quiz/submit', auth, async (req, res) => {
  const { quizId, answers } = req.body;

  const quiz = quizzes.find(q => q.id === quizId);
  if (!quiz) return res.status(404).json({ error: 'Quiz not found' });

  if (!answers || !Array.isArray(answers)) {
    return res.status(400).json({ error: 'Answers must be an array' });
  }

  let totalScore = 0;
  let formattedAnswers = [];

  for (let i = 0; i < answers.length; i++) {
    const selectedIndex = answers[i]; // selected option index (0-3)
    if (selectedIndex === null || selectedIndex === undefined) continue;

    const questionObj = quiz.questions[i];
    const selectedOption = questionObj.options[selectedIndex];
    const score = questionObj.scores[selectedIndex];

    totalScore += score;

    formattedAnswers.push({
      question: questionObj.question,
      selectedOption,
      score
    });
  }

  const avgScore = totalScore / formattedAnswers.length;
  const resultIndex = Math.min(Math.floor(avgScore) - 1, quiz.resultText.length - 1);
  const resultText = quiz.resultText[resultIndex] || "No result found";

  // Save to DB
  const quizResult = new QuizResult({
    userId: req.user.userId,
    quizId,
    title: quiz.title,
    answers: formattedAnswers,
    totalScore,
    resultText
  });

  await quizResult.save();

  res.json({ message: "Quiz submitted successfully", totalScore, resultText });
});



// Get quiz result history for the logged-in user
app.get('/quiz/history', auth, async (req, res) => {
  try {
    const results = await QuizResult.find({ userId: req.user.userId }).sort({ createdAt: -1 });
    res.json(results);
  } catch (error) {
    console.error("Error fetching quiz history:", error);
    res.status(500).json({ error: "Failed to fetch quiz history" });
  }
});


app.post("/mood", auth, async (req, res) => {
  try {
    const { responses } = req.body; // Should be an array of { question, answer }

    if (!Array.isArray(responses) || responses.length === 0) {
      return res.status(400).json({ error: "Responses are required." });
    }

    // Convert responses array to a prompt string
    const formattedPrompt = responses
    .map((r) => `Q: ${r.question}\nA: ${r.answer}`)
      .join("\n");
    
    console.log("Formatted Prompt:::::::::::\n" + formattedPrompt);

    // Send responses to Python API for analysis
    const analysisResponse = await axios.post("http://127.0.0.1:3002/analyze_mood", {
      content: formattedPrompt,
    });
    const { mental_score, eq_score, self_awareness_score } = analysisResponse.data;

    // Save the data to MongoDB
    const newMood = new Mood({
      userId: req.user.userId,
      responses,
      mental_score,
      eq_score,
      self_awareness_score
    });

    await newMood.save();

    res.status(201).json({
      message: "Mood analysis entry saved successfully",
      scores: {
        mental_score,
        eq_score,
        self_awareness_score
      }
    });
  } catch (error) {
    console.error("Error in /mood POST:", error);
    res.status(500).json({ error: "Failed to save mood analysis entry" });
  }
});

app.get("/api/generate-analysis", async (req, res) => {
  try {
      const journal = await Journal.findOne().sort({ createdAt: -1 }).limit(1); 
      const mood = await Mood.findOne().sort({ createdAt: -1 }).limit(1); 
      const quizResult = await QuizResult.findOne().sort({ createdAt: -1 }).limit(1); 

      if (!journal || !mood || !quizResult) {
          return res.status(400).json({ error: "Missing data for analysis report." });
      }

      const analysisData = {
        journal_score: journal.score, 
        self_awareness_score: mood.self_awareness_score,
        mental_score:mood.mental_score,
        eq_score: mood.eq_score, 
        quiz_score: quizResult.totalScore 
      };
    
        // Send responses to Python API for analysis
        const analysisResponse = await axios.post("http://127.0.0.1:3002/analyze_report", {
          content: analysisData,
        });
    analysis = analysisResponse.data;
    console.log("Analysis Data to be sent:",analysisData)
      res.json({
        analysis: analysis.analysis, // text paragraph from Python
        scores: analysisData,         // original scores (to plot bar chart)
      });
  } catch (error) {
      console.error("Error generating analysis report:", error);
      res.status(500).json({ error: "Failed to generate analysis report." });
  }
});

app.get('/journal/:userId', auth, async (req, res) => {
  console.log("✔️ Journal route hit:", req.params.userId);
  const { userId } = req.params;
  try {
    const entries = await Journal.find({ userId }); // Make sure field is 'userId'
    res.json(entries);
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Error fetching journal entries' });
  }
});

app.get('/mood/:userId', auth, async (req, res) => {
  console.log("✔️ Mood route hit:", req.params.userId);
  const { userId } = req.params;
  try {
    const logs = await Mood.find({ userId });
    res.json(logs);
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Error fetching mood logs' });
  }
});

app.get('/quiz/:userId', auth, async (req, res) => {
  console.log("✔️ Quiz route hit:", req.params.userId);
  const { userId } = req.params;
  try {
    const answers = await QuizResult.find({ userId });
    res.json(answers);
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Error fetching quiz answers' });
  }
});

// Start server
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));