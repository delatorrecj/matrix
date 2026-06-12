import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  createScenario,
  AmbiguousScenarioError,
  ApiUnreachableError,
  API_BASE_URL,
} from '@/lib/api';

function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe('createScenario', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('POSTs {query, input_type: "nl"} and returns the parsed scenario', async () => {
    const payload = {
      scenario_id: 'scn-9',
      description: 'BRT on Diversion Rd',
      corridor: 'diversion',
      lanes_closed: 1,
    };
    fetchMock.mockResolvedValue(jsonResponse(200, payload));

    const result = await createScenario('Run a BRT line along Diversion Road');

    expect(result).toEqual(payload);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/scenario`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({
      query: 'Run a BRT line along Diversion Road',
      input_type: 'nl',
    });
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/json');
  });

  it('throws AmbiguousScenarioError with the clarification on 400 + is_ambiguous', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(400, { error: 'Which corridor do you mean?', is_ambiguous: true })
    );

    await expect(createScenario('vague')).rejects.toThrowError(AmbiguousScenarioError);
    fetchMock.mockResolvedValue(
      jsonResponse(400, { error: 'Which corridor do you mean?', is_ambiguous: true })
    );
    await expect(createScenario('vague')).rejects.toThrow('Which corridor do you mean?');
  });

  it('throws ApiUnreachableError when fetch itself fails (API down)', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(createScenario('anything')).rejects.toThrowError(ApiUnreachableError);
  });

  it('throws a plain Error with the status for other non-2xx responses', async () => {
    fetchMock.mockResolvedValue(jsonResponse(500, { detail: 'boom' }));

    await expect(createScenario('anything')).rejects.toThrow(
      'Scenario request failed (HTTP 500)'
    );
  });
});
