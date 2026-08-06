import { z } from "zod";

export const uuidSchema = z.uuid();
export const isoTimestampSchema = z.iso.datetime({ offset: true });
