// models/QuizResult.js
// const mongoose = require("mongoose");

// const quizResultSchema = new mongoose.Schema({
//   userId: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
//   quizId: { type: Number, required: true },
//   answers: [{ type: Number }], // Store scores (e.g., [1,2,4])
//   totalScore: Number,
//   percentage: Number,
//   resultText: String,
//   timestamp: { type: Date, default: Date.now }
// });

// const QuizResult = mongoose.model("QuizResult", quizResultSchema);
// module.exports = QuizResult;


const mongoose = require('mongoose');

const AnswerSchema = new mongoose.Schema({
  question: String,
  selectedOption: String,
  score: Number
});

const QuizResultSchema = new mongoose.Schema({
  userId: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
  quizId: { type: Number, required: true },
  title: { type: String },
  answers: [AnswerSchema],
  totalScore: Number,
  resultText: String,
  timestamp: { type: Date, default: Date.now }
});

module.exports = mongoose.model("QuizResult", QuizResultSchema);
