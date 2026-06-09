import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import ValidationPanel from '@/components/ValidationPanel';

describe('ValidationPanel', () => {
  it('renders without crashing', () => {
    render(<ValidationPanel />);
    expect(screen.getByText(/Validation & Back-Testing/i)).toBeInTheDocument();
  });

  it('displays the RMSE metric', () => {
    render(<ValidationPanel />);
    expect(screen.getAllByText(/RMSE/i).length).toBeGreaterThan(0);
  });
});
