export interface NumericLimits {
  readonly max: number;
  readonly min: number;
}

export const ALERT_COOLDOWN_LIMITS: NumericLimits = { min: 0, max: 3600 };
export const CONFIDENCE_THRESHOLD_LIMITS: NumericLimits = { min: 0, max: 1 };
export const INFERENCE_FPS_LIMITS: NumericLimits = { min: 1, max: 15 };
export const DURATION_SECONDS_LIMITS: NumericLimits = { min: 1, max: 3600 };
export const DAY_HOUR_LIMITS: NumericLimits = { min: 0, max: 23 };
export const DETECTION_COUNT_LIMITS: NumericLimits = { min: 0, max: 1000 };
export const AREA_FRACTION_LIMITS: NumericLimits = { min: 0, max: 1 };
export const WEEKDAY_LIMITS: NumericLimits = { min: 0, max: 6 };

export const TEXT_LIMITS = {
  cameraName: 128,
  classLabel: 128,
  commentText: 2000,
  credentialId: 36,
  discordMessage: 2000,
  emailBody: 8192,
  emailSubject: 998,
  emailTo: 320,
  mqttPayload: 8192,
  mqttTopic: 512,
  objectClass: 256,
  slackMessage: 4096,
  sourceUrl: 2048,
  telegramChatId: 64,
  telegramMessage: 4096,
  workflowDescription: 2000,
  workflowName: 128,
} as const;
