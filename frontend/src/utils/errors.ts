import axios from 'axios';

/**
 * Extracts human-readable error messages from Axios / DRF API responses.
 * Handles field errors (e.g. { email: ["Already exists"] }), detail strings, and network errors.
 */
export function getErrorMessage(err: unknown, defaultMessage = 'An unexpected error occurred.'): string {
  if (axios.isAxiosError(err) && err.response?.data) {
    const data = err.response.data;
    if (typeof data === 'string') return data;
    if (data.detail && typeof data.detail === 'string') return data.detail;
    if (data.error && typeof data.error === 'string') return data.error;
    if (data.message && typeof data.message === 'string') return data.message;

    // Django REST Framework field-level validation errors
    if (typeof data === 'object' && data !== null) {
      const messages: string[] = [];
      for (const [key, val] of Object.entries(data)) {
        const label = key === 'non_field_errors' || key === 'detail' ? '' : `${key.replace(/_/g, ' ')}: `;
        if (Array.isArray(val)) {
          messages.push(`${label}${val.join(' ')}`);
        } else if (typeof val === 'string') {
          messages.push(`${label}${val}`);
        }
      }
      if (messages.length > 0) {
        return messages.join(' | ');
      }
    }
  }

  if (err instanceof Error) {
    return err.message;
  }

  return defaultMessage;
}
