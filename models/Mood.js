const mongoose = require("mongoose");

const moodSchema = new mongoose.Schema({
  responses: [
    {
      question: { type: String, required: true },
      answer: { type: String, required: true }
    }
    ],
  userId: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
  mental_score: { type: Number, required: true },
  eq_score: { type: Number, required: true },
  self_awareness_score: { type: Number, required: true }
}, { timestamps: true });

const Mood = mongoose.model("Mood", moodSchema);
module.exports = Mood;
