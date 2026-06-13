import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WeatherForm } from '../components/WeatherForm';

describe('WeatherForm', () => {
  it('renders input and submit button', () => {
    render(<WeatherForm onSubmit={() => {}} isLoading={false} />);
    expect(screen.getByLabelText(/city/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /get recommendations/i })).toBeInTheDocument();
  });

  it('calls onSubmit with city when form submitted', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<WeatherForm onSubmit={onSubmit} isLoading={false} />);

    await user.type(screen.getByLabelText(/city/i), 'Zagreb');
    await user.click(screen.getByRole('button', { name: /get recommendations/i }));

    expect(onSubmit).toHaveBeenCalledWith('Zagreb', undefined);
  });

  it('disables submit when loading', () => {
    render(<WeatherForm onSubmit={() => {}} isLoading={true} />);
    expect(screen.getByRole('button', { name: /analyzing/i })).toBeDisabled();
  });

  it('renders popular city buttons', () => {
    render(<WeatherForm onSubmit={() => {}} isLoading={false} />);
    expect(screen.getByRole('button', { name: 'Zagreb' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'London' })).toBeInTheDocument();
  });

  it('submits when popular city clicked', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<WeatherForm onSubmit={onSubmit} isLoading={false} />);

    await user.click(screen.getByRole('button', { name: 'Zagreb' }));

    expect(onSubmit).toHaveBeenCalledWith('Zagreb', undefined);
  });
});
