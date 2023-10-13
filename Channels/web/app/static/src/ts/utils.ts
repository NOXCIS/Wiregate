/**
 * Utility module with some general helper functions.
 */

/**
 * Sleep for the given time.
 * @param ms  number of milliseconds to sleep for.
 */
export function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}