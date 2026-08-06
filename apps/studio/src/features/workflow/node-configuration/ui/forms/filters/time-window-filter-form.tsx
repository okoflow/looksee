"use client";

import { Field, FieldGroup } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { Switch } from "@/shared/ui/switch";
import { ToggleGroup, ToggleGroupItem } from "@/shared/ui/toggle-group";
import { DAY_HOUR_LIMITS, WEEKDAY_LIMITS } from "@/entities/workflow";
import { BoundedNumberField } from "../../fields/bounded-number-field";
import type { NodeFormProps } from "../../form-props";

const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] as const;

function parseWeekdays(values: string[]): number[] {
  return values
    .map(Number)
    .filter((value) => {
      return Number.isInteger(value) && value >= WEEKDAY_LIMITS.min && value <= WEEKDAY_LIMITS.max;
    })
    .sort((left, right) => {
      return left - right;
    });
}

export function TimeWindowFilterForm({ data, onChange }: NodeFormProps<"time_window_filter">) {
  const handleStartHourCommit = (startHour: number) => {
    onChange({ ...data, start_hour: startHour });
  };

  const handleEndHourCommit = (endHour: number) => {
    onChange({ ...data, end_hour: endHour });
  };

  const handleWeekdaysChange = (values: string[]) => {
    onChange({ ...data, weekdays: parseWeekdays(values) });
  };

  const handleInvertChange = (invert: boolean) => {
    onChange({ ...data, invert });
  };

  return (
    <>
      <FieldGroup className="grid grid-cols-2 gap-2">
        <BoundedNumberField
          id="time-window-start-hour"
          isInteger
          label="Start hour"
          limits={DAY_HOUR_LIMITS}
          onCommit={handleStartHourCommit}
          value={data.start_hour}
        />

        <BoundedNumberField
          id="time-window-end-hour"
          isInteger
          label="End hour"
          limits={DAY_HOUR_LIMITS}
          onCommit={handleEndHourCommit}
          value={data.end_hour}
        />
      </FieldGroup>

      <Field>
        <HintedFieldLabel hint="Days when the window applies." id="time-window-weekdays">
          Weekdays
        </HintedFieldLabel>

        <ToggleGroup
          aria-labelledby="time-window-weekdays"
          className="flex-wrap justify-start"
          multiple
          onValueChange={handleWeekdaysChange}
          size="sm"
          value={data.weekdays.map(String)}
          variant="outline"
        >
          {WEEKDAY_LABELS.map((label, index) => {
            return (
              <ToggleGroupItem key={label} value={String(index)}>
                {label}
              </ToggleGroupItem>
            );
          })}
        </ToggleGroup>
      </Field>

      <Field className="justify-between" orientation="horizontal">
        <HintedFieldLabel hint="Pass events outside the window instead of inside." htmlFor="time-window-invert">
          Outside schedule
        </HintedFieldLabel>

        <Switch checked={data.invert} id="time-window-invert" onCheckedChange={handleInvertChange} />
      </Field>
    </>
  );
}
