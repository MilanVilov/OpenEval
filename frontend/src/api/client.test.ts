import { describe, expect, it, vi, afterEach } from 'vitest';

import { apiFetch, formatApiErrorMessage } from './client';

describe('formatApiErrorMessage', () => {
  it('returns string detail responses directly', () => {
    expect(formatApiErrorMessage(404, '{"detail":"Configuration not found"}')).toBe('Configuration not found');
  });

  it('formats validation errors into readable messages', () => {
    const body = JSON.stringify({
      detail: [
        {
          type: 'value_error',
          loc: ['body', 'graders'],
          msg: 'At least one grader is required',
        },
      ],
    });

    expect(formatApiErrorMessage(422, body)).toBe('Graders: At least one grader is required');
  });

  it('falls back to a generic message when the body is empty', () => {
    expect(formatApiErrorMessage(500, '')).toBe('Request failed with status 500.');
  });
});

describe('apiFetch', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('throws ApiError with a readable validation message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: [
              {
                loc: ['body', 'graders'],
                msg: 'At least one grader is required',
              },
            ],
          }),
          {
            status: 422,
            headers: { 'Content-Type': 'application/json' },
          },
        ),
      ),
    );

    await expect(apiFetch('/configs', { method: 'POST' })).rejects.toEqual(
      expect.objectContaining({
        message: 'Graders: At least one grader is required',
        status: 422,
      }),
    );
  });
});
