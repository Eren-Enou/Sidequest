import { useState } from "react";
import { Field, SelectField } from "../components/UI.jsx";

export default function FinishForm({
  suggestedMinutes,
  onSubmit,
  onCancel,
  busy,
}) {
  const [values, setValues] = useState({
    actual_duration_minutes: suggestedMinutes,
    enjoyment_rating: "",
    progress: "",
    notes: "",
    mark_goal_completed: false,
  });
  const [validation, setValidation] = useState("");
  const change = (key, value) =>
    setValues((previous) => ({ ...previous, [key]: value }));
  function submit(event) {
    event.preventDefault();
    if (!Number.isInteger(values.enjoyment_rating) || values.enjoyment_rating < 1 || values.enjoyment_rating > 5) {
      setValidation("Choose an enjoyment rating from 1 to 5.");
      return;
    }
    if (
      !Number.isInteger(values.actual_duration_minutes) ||
      values.actual_duration_minutes < 1 ||
      !values.progress.trim()
    ) {
      setValidation(
        "Enter a positive whole number of minutes and describe your progress.",
      );
      return;
    }
    setValidation("");
    onSubmit({
      ...values,
      progress: values.progress.trim(),
      notes: values.notes || null,
    });
  }
  return (
    <form
      className="editor finish-form"
      aria-label="Finish Sidequest"
      onSubmit={submit}
    >
      <h2>How did it go?</h2>
      <fieldset disabled={busy}>
        <div className="form-row">
          <Field
            label="Actual play time (minutes)"
            hint="Suggested from elapsed time. Adjust for breaks or time spent away — this is your actual play time."
          >
            <input
              type="number"
              min="1"
              step="1"
              required
              value={values.actual_duration_minutes}
              onChange={(e) =>
                change(
                  "actual_duration_minutes",
                  e.target.value === "" ? "" : Number(e.target.value),
                )
              }
            />
          </Field>
          <SelectField
            label="How much did you enjoy it?"
            value={values.enjoyment_rating}
            required
            onChange={(value) => change("enjoyment_rating", value === "" ? "" : Number(value))}
            options={[
              ["", "Choose a rating…"],
              [1, "1 · Not enjoyable"],
              [2, "2 · A little"],
              [3, "3 · Okay"],
              [4, "4 · Good"],
              [5, "5 · Loved it"],
            ]}
          />
        </div>
        <Field
          label="Progress"
          hint="What happened? A little progress, a big win, or no progress are all worth recording."
        >
          <textarea
            required
            rows="3"
            placeholder="Level 23 → 25, finished chapter 4, or didn’t make much progress…"
            value={values.progress}
            onChange={(e) => change("progress", e.target.value)}
          />
        </Field>
        <Field label="Session notes (optional)">
          <textarea
            rows="2"
            value={values.notes}
            onChange={(e) => change("notes", e.target.value)}
          />
        </Field>
        <label className="inline-check completion-check">
          <input
            type="checkbox"
            checked={values.mark_goal_completed}
            onChange={(e) => change("mark_goal_completed", e.target.checked)}
          />
          Mark this goal completed
        </label>
        <p className="quiet">
          Only mark it complete if the whole goal is done. Otherwise, you can
          keep working on it next time.
        </p>
      </fieldset>
      {validation && (
        <p className="notice error" role="alert">
          {validation}
        </p>
      )}
      <div className="actions">
        <button className="primary" disabled={busy}>
          {busy ? "Saving Sidequest…" : "Save completed Sidequest"}
        </button>
        <button type="button" onClick={onCancel} disabled={busy}>
          Keep playing
        </button>
      </div>
    </form>
  );
}
