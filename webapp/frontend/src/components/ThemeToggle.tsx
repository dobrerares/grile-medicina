import { useTheme } from "../hooks/useTheme";

const options = [
  { value: "light" as const, icon: "\u2600\uFE0F", label: "Luminos" },
  { value: "dark" as const, icon: "\uD83C\uDF19", label: "Intunecat" },
  { value: "system" as const, icon: "\uD83D\uDCBB", label: "Sistem" },
];

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="theme-toggle" role="radiogroup" aria-label="Tema">
      {options.map((opt) => (
        <button
          key={opt.value}
          className={`theme-toggle-btn${theme === opt.value ? " theme-toggle-active" : ""}`}
          onClick={() => setTheme(opt.value)}
          aria-checked={theme === opt.value}
          role="radio"
          title={opt.label}
          type="button"
        >
          <span aria-hidden="true">{opt.icon}</span>
        </button>
      ))}
    </div>
  );
}
