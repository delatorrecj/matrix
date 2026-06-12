import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import MatrixCockpit from '@/app/page';
import { API_BASE_URL } from '@/lib/api';

// --- Heavy map/WebGL modules are not jsdom-compatible: stub them out. ---
const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock }),
}));
vi.mock('react-map-gl/maplibre', () => ({
  Map: () => null,
}));
vi.mock('maplibre-gl', () => ({ default: {} }));
vi.mock('@deck.gl/react', () => ({
  default: ({ children }: { children?: React.ReactNode }) => <div data-testid="deckgl">{children}</div>,
}));
vi.mock('@deck.gl/layers', () => ({
  PolygonLayer: vi.fn(),
}));

const SCENARIO_OK = {
  scenario_id: 'scn-123',
  description: 'school in Molo',
  corridor: 'molo',
  lanes_closed: 0,
};

function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe('MatrixCockpit scenario submission', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    pushMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('POSTs the query to /scenario and navigates to the scenario page', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, SCENARIO_OK));
    render(<MatrixCockpit />);

    fireEvent.change(screen.getByLabelText(/Scenario Query/i), {
      target: { value: 'What if we build a 3,000-seat school in Molo?' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Simulate Scenario/i }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith('/scenario/scn-123'));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/scenario`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({
      query: 'What if we build a 3,000-seat school in Molo?',
      input_type: 'nl',
    });
  });

  it('shows a loading state while the request is in flight', async () => {
    let resolveFetch!: (value: Response) => void;
    fetchMock.mockReturnValue(new Promise<Response>((resolve) => { resolveFetch = resolve; }));
    render(<MatrixCockpit />);

    fireEvent.change(screen.getByLabelText(/Scenario Query/i), {
      target: { value: 'Close one lane on Diversion Road' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Simulate Scenario/i }));

    const pending = await screen.findByRole('button', { name: /Parsing scenario/i });
    expect(pending).toBeDisabled();
    // Presets are disabled too while in flight.
    expect(screen.getByRole('button', { name: 'School in Molo' })).toBeDisabled();

    resolveFetch(jsonResponse(200, SCENARIO_OK));
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith('/scenario/scn-123'));
  });

  it('renders the clarification message inline on a 400 ambiguous response', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(400, { error: 'Which corridor do you mean?', is_ambiguous: true })
    );
    render(<MatrixCockpit />);

    fireEvent.change(screen.getByLabelText(/Scenario Query/i), {
      target: { value: 'do something somewhere' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Simulate Scenario/i }));

    expect(await screen.findByText('Which corridor do you mean?')).toBeInTheDocument();
    expect(screen.getByText(/Clarification needed/i)).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
    // No sample mode for an ambiguous query — the API is reachable.
    expect(screen.queryByText(/Sample mode/i)).not.toBeInTheDocument();
  });

  it('shows the labeled "Sample mode — API offline" state on network failure', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    render(<MatrixCockpit />);

    fireEvent.change(screen.getByLabelText(/Scenario Query/i), {
      target: { value: 'What if we build a 3,000-seat school in Molo?' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Simulate Scenario/i }));

    expect(await screen.findByText(/Sample mode — API offline/i)).toBeInTheDocument();
    // Sample cards are explicitly labeled — never presented as real results.
    expect(screen.getByText('Economic (sample)')).toBeInTheDocument();
    expect(screen.getByText('Behavioral (sample)')).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it('submits a preset query when a reference scenario is clicked', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, SCENARIO_OK));
    render(<MatrixCockpit />);

    fireEvent.click(screen.getByRole('button', { name: 'School in Molo' }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith('/scenario/scn-123'));
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init.body)).toEqual({
      query: 'What if we build a 3,000-seat school in Molo?',
      input_type: 'nl',
    });
  });

  it('renders no dimension results before any submission (no unlabeled mock data)', () => {
    fetchMock.mockResolvedValue(jsonResponse(200, SCENARIO_OK));
    render(<MatrixCockpit />);

    expect(screen.queryByText(/Sample mode/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Economic/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Behavioral/)).not.toBeInTheDocument();
  });
});
