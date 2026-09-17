export const APP_VERSION = '0.14.5'
export async function resolveAppVersion(
  _appVersionRoot: string,
  _viteAppVersion?: string
): Promise<string> { 
  return APP_VERSION 
}
