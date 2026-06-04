export interface ModelOption {
  value: string;
  label: string;
}

export interface ModelGroup {
  group: string;
  models: ModelOption[];
}

export interface ReasoningEffortOption {
  value: 'low' | 'medium' | 'high' | 'xhigh';
  label: string;
}

const OPENAI_CONFIG_MODEL_GROUPS: ModelGroup[] = [
  {
    group: 'Frontier',
    models: [
      { value: 'gpt-5.5', label: 'GPT-5.5' },
      { value: 'gpt-5.5-pro', label: 'GPT-5.5 Pro' },
      { value: 'gpt-5.4', label: 'GPT-5.4' },
      { value: 'gpt-5.4-pro', label: 'GPT-5.4 Pro' },
      { value: 'gpt-5.4-mini', label: 'GPT-5.4 Mini' },
      { value: 'gpt-5.4-nano', label: 'GPT-5.4 Nano' },
    ],
  },
  {
    group: 'GPT-5 Family',
    models: [
      { value: 'gpt-5.3-codex', label: 'GPT-5.3 Codex' },
      { value: 'gpt-5.2', label: 'GPT-5.2' },
      { value: 'gpt-5.2-pro', label: 'GPT-5.2 Pro' },
      { value: 'gpt-5.1', label: 'GPT-5.1' },
      { value: 'gpt-5', label: 'GPT-5' },
      { value: 'gpt-5-pro', label: 'GPT-5 Pro' },
      { value: 'gpt-5-mini', label: 'GPT-5 Mini' },
      { value: 'gpt-5-nano', label: 'GPT-5 Nano' },
    ],
  },
  {
    group: 'Non-reasoning',
    models: [
      { value: 'gpt-4.1', label: 'GPT-4.1' },
      { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini' },
      { value: 'gpt-4.1-nano', label: 'GPT-4.1 Nano' },
      { value: 'gpt-4o', label: 'GPT-4o' },
      { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
    ],
  },
  {
    group: 'Reasoning (o-series)',
    models: [
      { value: 'o3', label: 'o3' },
      { value: 'o3-pro', label: 'o3 Pro' },
      { value: 'o3-mini', label: 'o3 Mini' },
      { value: 'o4-mini', label: 'o4 Mini' },
    ],
  },
];

const REASONING_EFFORT_OPTIONS: Record<string, ReasoningEffortOption[]> = {
  'gpt-5.5': [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'xhigh', label: 'Extra High' },
  ],
  'gpt-5.5-pro': [
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'xhigh', label: 'Extra High' },
  ],
  'gpt-5.4': [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'xhigh', label: 'Extra High' },
  ],
  'gpt-5.4-pro': [
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'xhigh', label: 'Extra High' },
  ],
  'gpt-5.4-mini': [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'xhigh', label: 'Extra High' },
  ],
  'gpt-5.4-nano': [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'xhigh', label: 'Extra High' },
  ],
  'gpt-5.3-codex': [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'xhigh', label: 'Extra High' },
  ],
  'gpt-5.2': [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'xhigh', label: 'Extra High' },
  ],
  'gpt-5.2-pro': [
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'xhigh', label: 'Extra High' },
  ],
  'gpt-5.1': [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
  ],
  'gpt-5': [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
  ],
  'gpt-5-pro': [{ value: 'high', label: 'High' }],
  'gpt-5-mini': [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
  ],
  'gpt-5-nano': [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
  ],
  o3: [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'xhigh', label: 'Extra High' },
  ],
  'o3-pro': [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'xhigh', label: 'Extra High' },
  ],
  'o3-mini': [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'xhigh', label: 'Extra High' },
  ],
  'o4-mini': [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'xhigh', label: 'Extra High' },
  ],
};

export const OPENAI_CONFIG_MODEL_OPTIONS: ModelGroup[] = OPENAI_CONFIG_MODEL_GROUPS;

export const OPENAI_GRADER_MODEL_OPTIONS: ModelGroup[] = [
  {
    group: '',
    models: [{ value: '', label: 'Same as config model (default)' }],
  },
  ...OPENAI_CONFIG_MODEL_GROUPS,
];

export function getReasoningEffortOptions(model: string): ReasoningEffortOption[] {
  return REASONING_EFFORT_OPTIONS[model] ?? [];
}

export function supportsReasoning(model: string): boolean {
  return getReasoningEffortOptions(model).length > 0;
}
