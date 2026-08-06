"use client";

import type { AlertSeverity } from "@/entities/alert";
import { ALERT_COOLDOWN_LIMITS } from "@/entities/workflow";
import { BoundedNumberField } from "../../fields/bounded-number-field";
import { SelectField, type SelectOption } from "../../fields/select-field";
import type { NodeFormProps } from "../../form-props";

const ALERT_SEVERITY_OPTIONS: readonly SelectOption<AlertSeverity>[] = [
  { label: "Info", value: "info" },
  { label: "Warning", value: "warning" },
  { label: "Critical", value: "critical" },
];

export function LogAlertActionForm({ data, onChange }: NodeFormProps<"log_alert_action">) {
  const handleSeverityChange = (severity: AlertSeverity) => {
    onChange({ ...data, severity });
  };

  const handleCooldownCommit = (cooldown_seconds: number) => {
    onChange({ ...data, cooldown_seconds });
  };

  return (
    <>
      <SelectField
        id="log-alert-severity"
        label="Severity"
        onValueChange={handleSeverityChange}
        options={ALERT_SEVERITY_OPTIONS}
        value={data.severity}
      />

      <BoundedNumberField
        description="Drop repeats from the same camera within the window; 0 records every event."
        id="log-alert-cooldown"
        isInteger
        label="Cooldown seconds"
        limits={ALERT_COOLDOWN_LIMITS}
        onCommit={handleCooldownCommit}
        value={data.cooldown_seconds}
      />
    </>
  );
}
