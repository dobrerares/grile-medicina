// --- Correct answer toasts ---
const CORRECT_MESSAGES = [
  "Excelent!",
  "Foarte bine!",
  "Așa da!",
  "Perfect!",
  "Bravo!",
  "Corect!",
  "Impecabil!",
];

// --- Streak toasts (shown instead of CORRECT_MESSAGES when on a streak) ---
const STREAK_MESSAGES: Record<number, string> = {
  3: "Trei la rând! Continuă tot așa!",
  5: "Cinci corecte consecutiv! Ești în formă!",
  7: "Serie de 7! Ești de neoprit!",
  10: "10 corecte la rând! Incredibil!",
};

// --- Wrong answer toasts ---
const WRONG_MESSAGES = [
  "Nu renunța!",
  "Greșelile ne ajută să învățăm",
  "Data viitoare va fi mai bine",
  "Continuă, ești pe drumul cel bun!",
  "Răbdare — progresul vine cu exercițiu",
];

// --- Results page banners ---
interface ResultBanner {
  text: string;
  tone: "excellent" | "good" | "decent" | "encourage";
}

function getResultBanner(accuracy: number): ResultBanner {
  if (accuracy >= 0.9) return { text: "Rezultat extraordinar! Ești foarte bine pregătit!", tone: "excellent" };
  if (accuracy >= 0.7) return { text: "Foarte bine! Mai repetă capitolele unde ai greșit.", tone: "good" };
  if (accuracy >= 0.5) return { text: "Efort bun! Continuă să exersezi, progresul vine.", tone: "decent" };
  return { text: "Nu te descuraja — fiecare test te face mai bun. Revino și încearcă din nou!", tone: "encourage" };
}

// --- Dashboard messages ---
interface DashboardMessage {
  text: string;
  type: "streak" | "improvement" | "milestone" | "welcome";
}

function getDashboardMessages(
  _username: string,
  totalAnswered: number,
  studyStreak: number,
  accuracyTrend: number,
): DashboardMessage[] {
  const messages: DashboardMessage[] = [];

  if (studyStreak >= 3) {
    messages.push({ text: `${studyStreak} zile consecutive de studiu!`, type: "streak" });
  }

  if (accuracyTrend > 0) {
    messages.push({
      text: `Ai crescut cu ${Math.round(accuracyTrend * 100)}% luna aceasta!`,
      type: "improvement",
    });
  }

  const milestones = [10000, 5000, 1000, 500, 100];
  for (const m of milestones) {
    if (totalAnswered >= m) {
      messages.push({ text: `Ai răspuns la ${m.toLocaleString("ro-RO")} întrebări în total!`, type: "milestone" });
      break;
    }
  }

  return messages;
}

// --- Helpers ---
function pickRandom<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function getCorrectToast(streak: number): string {
  if (STREAK_MESSAGES[streak]) return STREAK_MESSAGES[streak];
  if (streak > 10 && streak % 5 === 0) return `Serie de ${streak}! Ești de neoprit!`;
  return pickRandom(CORRECT_MESSAGES);
}

function getWrongToast(): string {
  return pickRandom(WRONG_MESSAGES);
}

export { getCorrectToast, getWrongToast, getResultBanner, getDashboardMessages };
export type { ResultBanner, DashboardMessage };
