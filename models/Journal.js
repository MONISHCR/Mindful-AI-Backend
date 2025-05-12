const mongoose = require("mongoose");

const journalSchema = new mongoose.Schema({
  content: { type: String, required: true },
  userId: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
  score: { type: Number, required: true }, // Mental health score (1-10)
  explanation: { type: String, required: true }, // Why this score was given
  recommendation: { type: String, required: true }, // Suggested action for the user
}, { timestamps: true });

const Journal = mongoose.model("Journal", journalSchema);
module.exports = Journal;