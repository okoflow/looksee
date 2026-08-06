import type { PresetField, PresetParamLookup, PresetParams, WorkflowPreset } from "../config/presets";

function resolveNumericParam(field: PresetField, raw: string | number | undefined): number {
  const value = Number(raw);

  if (raw === "" || !Number.isFinite(value)) {
    return field.defaultValue;
  }

  const lowerBounded = field.min === undefined ? value : Math.max(field.min, value);

  return field.max === undefined ? lowerBounded : Math.min(field.max, lowerBounded);
}

export function resolvePresetParams(preset: WorkflowPreset, params: PresetParams): PresetParamLookup {
  const values = new Map(
    preset.fields.map((field): [string, number] => {
      return [field.key, resolveNumericParam(field, params[field.key])];
    })
  );

  return (key) => {
    const value = values.get(key);

    if (value === undefined) {
      throw new Error(`Unknown preset field "${key}"`);
    }

    return value;
  };
}
