import { HypeBarometer } from "@/components/hype-barometer";

const tools = [
  {
    name: "LangChain",
    score: 92,
    url: "https://github.com/langchain-ai/langchain",
    stats: { githubStars: "96.2k", hnMentions: 847, pypiDownloads: "12.4M/mo", lastUpdated: "2 hours ago" },
  },
  {
    name: "Ollama",
    score: 87,
    url: "https://github.com/ollama/ollama",
    stats: { githubStars: "108.5k", hnMentions: 623, pypiDownloads: "N/A", lastUpdated: "4 hours ago" },
  },
  {
    name: "Cursor",
    score: 85,
    url: "https://cursor.com",
    stats: { githubStars: "N/A", hnMentions: 512, pypiDownloads: "N/A", lastUpdated: "1 day ago" },
  },
  {
    name: "CrewAI",
    score: 78,
    url: "https://github.com/crewAIInc/crewAI",
    stats: { githubStars: "24.8k", hnMentions: 234, pypiDownloads: "1.8M/mo", lastUpdated: "6 hours ago" },
  },
  {
    name: "LlamaIndex",
    score: 72,
    url: "https://github.com/run-llama/llama_index",
    stats: { githubStars: "38.2k", hnMentions: 312, pypiDownloads: "4.2M/mo", lastUpdated: "3 hours ago" },
  },
  {
    name: "DSPy",
    score: 68,
    url: "https://github.com/stanfordnlp/dspy",
    stats: { githubStars: "21.4k", hnMentions: 189, pypiDownloads: "890k/mo", lastUpdated: "1 day ago" },
  },
  {
    name: "Anthropic Claude",
    score: 65,
    url: "https://anthropic.com",
    stats: { githubStars: "N/A", hnMentions: 1024, pypiDownloads: "2.1M/mo", lastUpdated: "12 hours ago" },
  },
  {
    name: "OpenAI GPT",
    score: 61,
    url: "https://openai.com",
    stats: { githubStars: "N/A", hnMentions: 2341, pypiDownloads: "18.7M/mo", lastUpdated: "1 day ago" },
  },
  {
    name: "Hugging Face",
    score: 55,
    url: "https://github.com/huggingface/transformers",
    stats: { githubStars: "142.3k", hnMentions: 567, pypiDownloads: "32.1M/mo", lastUpdated: "1 hour ago" },
  },
  {
    name: "Mistral",
    score: 52,
    url: "https://mistral.ai",
    stats: { githubStars: "N/A", hnMentions: 298, pypiDownloads: "N/A", lastUpdated: "2 days ago" },
  },
  {
    name: "Vercel AI SDK",
    score: 48,
    url: "https://github.com/vercel/ai",
    stats: { githubStars: "12.8k", hnMentions: 87, pypiDownloads: "N/A", lastUpdated: "5 hours ago" },
  },
  {
    name: "Semantic Kernel",
    score: 35,
    url: "https://github.com/microsoft/semantic-kernel",
    stats: { githubStars: "23.1k", hnMentions: 56, pypiDownloads: "320k/mo", lastUpdated: "8 hours ago" },
  },
  {
    name: "AutoGPT",
    score: 28,
    url: "https://github.com/Significant-Gravitas/AutoGPT",
    stats: { githubStars: "171.2k", hnMentions: 34, pypiDownloads: "45k/mo", lastUpdated: "3 days ago" },
  },
  {
    name: "BabyAGI",
    score: 15,
    url: "https://github.com/yoheinakajima/babyagi",
    stats: { githubStars: "20.8k", hnMentions: 12, pypiDownloads: "N/A", lastUpdated: "2 months ago" },
  },
];

export default function Home() {
  return (
    <main className="min-h-screen py-16 px-4">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-4xl font-bold text-foreground mb-10 text-center">
          🔥 Hype Barometer
        </h1>

        <div className="space-y-0">
          {tools.map((tool) => (
            <HypeBarometer
              key={tool.name}
              name={tool.name}
              score={tool.score}
              url={tool.url}
              stats={tool.stats}
            />
          ))}
        </div>
      </div>
    </main>
  );
}
