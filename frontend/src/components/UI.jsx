import { cloneElement, useId } from "react";

export function ErrorNotice({ message }) {
  return message ? (
    <div className="notice error" role="alert">
      {message}
    </div>
  ) : null;
}

export function Field({ label, children, hint }) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {cloneElement(children, {
        id,
        "aria-describedby": hint ? `${id}-hint` : undefined,
      })}
      {hint && <small id={`${id}-hint`}>{hint}</small>}
    </div>
  );
}

export function SelectField({
  label,
  value,
  onChange,
  options,
  hint,
  ...rest
}) {
  return (
    <Field label={label} hint={hint}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        {...rest}
      >
        {options.map(([key, text]) => (
          <option key={key} value={key}>
            {text}
          </option>
        ))}
      </select>
    </Field>
  );
}

export const energies = [
  ["low", "Low"],
  ["medium", "Medium"],
  ["high", "High"],
];
export const experiences = [
  ["progression", "Progression"],
  ["chill", "Chill"],
  ["challenge", "Challenge"],
  ["novelty", "Novelty"],
];
