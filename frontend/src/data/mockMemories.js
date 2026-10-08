export const initialMockMemories = [
  {
    id: "mem-1",
    person: "Rahul",
    category: "deadline",
    dateTime: "Today, 10:45 AM",
    topic: "Hackathon Submission",
    fact: "Rahul told me that our hackathon submission is Friday at 5 PM and we should use React.",
    tags: ["hackathon", "submission", "friday", "react"],
    importance: 5
  },
  {
    id: "mem-2",
    person: "Priya",
    category: "suggestion",
    dateTime: "Today, 09:20 AM",
    topic: "Demo Strategy",
    fact: "Priya mentioned that the judging criteria heavily weights live demo reliability, zero latency, and UI polish.",
    tags: ["demo", "judging", "ui"],
    importance: 4
  },
  {
    id: "mem-3",
    person: "Alex",
    category: "work",
    dateTime: "Yesterday, 04:15 PM",
    topic: "SerpApi Integration",
    fact: "Alex suggested integrating SerpApi so ECHO can seamlessly ground personal memory with current web information.",
    tags: ["serpapi", "web-search", "grounding"],
    importance: 4
  },
  {
    id: "mem-4",
    person: "Rahul",
    category: "suggestion",
    dateTime: "Yesterday, 02:00 PM",
    topic: "Audio Visuals",
    fact: "Rahul emphasized having dynamic waveform visuals so users have immediate feedback when speaking.",
    tags: ["waveform", "visuals", "ux"],
    importance: 3
  },
  {
    id: "mem-5",
    person: "Sara",
    category: "personal",
    dateTime: "Oct 1, 06:30 PM",
    topic: "Team Celebration",
    fact: "Sara recommended checking out the new Blue Bottle Coffee downtown for post-hackathon coffee.",
    tags: ["coffee", "team", "downtown"],
    importance: 2
  }
];

export const suggestedQueries = [
  "What did Rahul tell me about the hackathon?",
  "When is our submission deadline?",
  "What tech did Rahul suggest we use?",
  "What did Priya say about the demo?"
];

export const mockEchoResponses = {
  "What did Rahul tell me about the hackathon?": {
    answer: "Rahul told you that the hackathon submission is Friday at 5 PM and suggested that you should use React.",
    citedMemoryIds: ["mem-1"],
    webGrounded: false
  },
  "When is our submission deadline?": {
    answer: "Your hackathon submission deadline is this Friday at 5:00 PM, as confirmed by Rahul.",
    citedMemoryIds: ["mem-1"],
    webGrounded: false
  },
  "What tech did Rahul suggest we use?": {
    answer: "Rahul suggested using React for the hackathon project.",
    citedMemoryIds: ["mem-1"],
    webGrounded: false
  },
  "What did Priya say about the demo?": {
    answer: "Priya noted that the judging panel will prioritize live demo reliability, low latency, and visual UI polish.",
    citedMemoryIds: ["mem-2"],
    webGrounded: false
  }
};
