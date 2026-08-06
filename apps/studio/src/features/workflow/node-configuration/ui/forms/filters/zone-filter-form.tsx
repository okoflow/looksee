"use client";

import type { NormalizedPolygon } from "@/shared/lib/geometry";
import { Field } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { PointsPad } from "../../fields/points-pad";
import type { NodeFormProps } from "../../form-props";

export function ZoneFilterForm({ data, onChange, upstreamSource }: NodeFormProps<"zone_filter">) {
  const handlePolygonChange = (polygon: NormalizedPolygon) => {
    onChange({ ...data, polygon });
  };

  return (
    <Field>
      <HintedFieldLabel hint="Draw on the pad or open the camera preview.">Polygon</HintedFieldLabel>

      <PointsPad
        ariaLabel="Zone drawing pad"
        emptyLabel="not set"
        onChange={handlePolygonChange}
        points={data.polygon}
        previewTitle="Zone on camera preview"
        shape="polygon"
        unitLabel="corners"
        upstreamSource={upstreamSource ?? null}
      />
    </Field>
  );
}
