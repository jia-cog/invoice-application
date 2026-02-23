// Mock axios before it gets imported by the module under test.
// axios v1.x uses ESM so we must mock it for Jest.
const mockRequestHandlers = [];
const mockResponseHandlers = [];

jest.mock('axios', () => {
  const mockInstance = {
    defaults: {
      baseURL: '',
      headers: {},
    },
    interceptors: {
      request: {
        use: jest.fn((fulfilled, rejected) => {
          mockRequestHandlers.push({ fulfilled, rejected });
        }),
        handlers: mockRequestHandlers,
      },
      response: {
        use: jest.fn((fulfilled, rejected) => {
          mockResponseHandlers.push({ fulfilled, rejected });
        }),
        handlers: mockResponseHandlers,
      },
    },
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  };

  return {
    __esModule: true,
    default: {
      create: jest.fn((config) => {
        mockInstance.defaults.baseURL = config.baseURL;
        mockInstance.defaults.headers = config.headers;
        return mockInstance;
      }),
    },
  };
});

describe('API Module', () => {
  let api, authAPI, invoicesAPI, reportsAPI;

  beforeEach(() => {
    localStorage.clear();

    const apiModule = require('./api');
    api = apiModule.default;
    authAPI = apiModule.authAPI;
    invoicesAPI = apiModule.invoicesAPI;
    reportsAPI = apiModule.reportsAPI;
  });

  describe('axios instance configuration', () => {
    test('uses correct base URL from env or default', () => {
      expect(api.defaults.baseURL).toBe('http://localhost:5001/api');
    });

    test('sets Content-Type header to application/json', () => {
      expect(api.defaults.headers['Content-Type']).toBe('application/json');
    });
  });

  describe('request interceptor', () => {
    test('attaches token to request when present in localStorage', () => {
      localStorage.setItem('token', 'test-token-123');

      const requestConfig = { headers: {} };
      const fulfilled = mockRequestHandlers[0].fulfilled;
      const result = fulfilled(requestConfig);

      expect(result.headers.Authorization).toBe('Bearer test-token-123');
    });

    test('does NOT attach token when absent from localStorage', () => {
      const requestConfig = { headers: {} };
      const fulfilled = mockRequestHandlers[0].fulfilled;
      const result = fulfilled(requestConfig);

      expect(result.headers.Authorization).toBeUndefined();
    });

    test('rejects on request error', async () => {
      const rejected = mockRequestHandlers[0].rejected;
      const error = new Error('request error');

      await expect(rejected(error)).rejects.toThrow('request error');
    });
  });

  describe('response interceptor', () => {
    test('passes through successful responses', () => {
      const fulfilled = mockResponseHandlers[0].fulfilled;
      const response = { data: 'test', status: 200 };
      expect(fulfilled(response)).toBe(response);
    });

    test('clears localStorage and redirects on 401 error', async () => {
      localStorage.setItem('token', 'some-token');
      localStorage.setItem('user', 'some-user');

      delete window.location;
      window.location = { href: '' };

      const rejected = mockResponseHandlers[0].rejected;
      const error = { response: { status: 401 } };

      await expect(rejected(error)).rejects.toEqual(error);

      expect(localStorage.getItem('token')).toBeNull();
      expect(localStorage.getItem('user')).toBeNull();
      expect(window.location.href).toBe('/login');
    });

    test('does not redirect on non-401 errors', async () => {
      localStorage.setItem('token', 'some-token');

      delete window.location;
      window.location = { href: '/current-page' };

      const rejected = mockResponseHandlers[0].rejected;
      const error = { response: { status: 500 } };

      await expect(rejected(error)).rejects.toEqual(error);

      expect(localStorage.getItem('token')).toBe('some-token');
      expect(window.location.href).toBe('/current-page');
    });
  });

  describe('authAPI', () => {
    beforeEach(() => {
      api.post.mockResolvedValue({ data: {} });
      api.get.mockResolvedValue({ data: {} });
    });

    test('register calls POST /auth/register with userData', async () => {
      const userData = { username: 'test', email: 'test@test.com', password: 'pass123' };
      await authAPI.register(userData);
      expect(api.post).toHaveBeenCalledWith('/auth/register', userData);
    });

    test('login calls POST /auth/login with credentials', async () => {
      const credentials = { username: 'test', password: 'pass123' };
      await authAPI.login(credentials);
      expect(api.post).toHaveBeenCalledWith('/auth/login', credentials);
    });

    test('getProfile calls GET /auth/profile', async () => {
      await authAPI.getProfile();
      expect(api.get).toHaveBeenCalledWith('/auth/profile');
    });
  });

  describe('invoicesAPI', () => {
    beforeEach(() => {
      api.get.mockResolvedValue({ data: {} });
      api.post.mockResolvedValue({ data: {} });
      api.put.mockResolvedValue({ data: {} });
      api.delete.mockResolvedValue({ data: {} });
    });

    test('getAll calls GET /invoices/', async () => {
      await invoicesAPI.getAll();
      expect(api.get).toHaveBeenCalledWith('/invoices/');
    });

    test('getById calls GET /invoices/:id', async () => {
      await invoicesAPI.getById(42);
      expect(api.get).toHaveBeenCalledWith('/invoices/42');
    });

    test('create calls POST /invoices/ with invoiceData', async () => {
      const data = { customer_name: 'Acme' };
      await invoicesAPI.create(data);
      expect(api.post).toHaveBeenCalledWith('/invoices/', data);
    });

    test('update calls PUT /invoices/:id with invoiceData', async () => {
      const data = { customer_name: 'Acme Updated' };
      await invoicesAPI.update(5, data);
      expect(api.put).toHaveBeenCalledWith('/invoices/5', data);
    });

    test('delete calls DELETE /invoices/:id', async () => {
      await invoicesAPI.delete(5);
      expect(api.delete).toHaveBeenCalledWith('/invoices/5');
    });
  });

  describe('reportsAPI', () => {
    beforeEach(() => {
      api.get.mockResolvedValue({ data: {} });
      api.post.mockResolvedValue({ data: {} });
      api.delete.mockResolvedValue({ data: {} });
    });

    test('getAll calls GET /reports/', async () => {
      await reportsAPI.getAll();
      expect(api.get).toHaveBeenCalledWith('/reports/');
    });

    test('generate calls POST /reports/generate with reportData', async () => {
      const data = { report_type: 'monthly', start_date: '2025-01-01', end_date: '2025-01-31' };
      await reportsAPI.generate(data);
      expect(api.post).toHaveBeenCalledWith('/reports/generate', data);
    });

    test('getDashboard calls GET /reports/dashboard', async () => {
      await reportsAPI.getDashboard();
      expect(api.get).toHaveBeenCalledWith('/reports/dashboard');
    });

    test('delete calls DELETE /reports/:id', async () => {
      await reportsAPI.delete(3);
      expect(api.delete).toHaveBeenCalledWith('/reports/3');
    });
  });
});
