import shlex
#import subprocess
import asyncio
import time
import sys
from pprint import pprint


async def run_command(*args):
    """
    Run command in subprocess.

    Example from:
        http://asyncio.readthedocs.io/en/latest/subprocess.html
    """
    # Create subprocess
    process = await asyncio.create_subprocess_exec(
        *args, 
        stdout=asyncio.subprocess.PIPE, 
        stderr=asyncio.subprocess.PIPE        
    )

    # Status
    print(f"Started: {args}, pid={process.pid}",flush=True)

    # Wait for the subprocess to finish
    stdout, stderr = await process.communicate()

    # Progress
    if process.returncode == 0:
        print(f"Done: {args}, pid={process.pid}, result: {stdout.decode().strip()}",flush=True,)
    else:
        print(f"Failed: {args}, pid={process.pid}, result:{stderr.decode().strip()}",flush=True,)

    # Result
    result = stdout.decode().strip()

    # Return stdout
    return result

def make_chunks(l, n):
    """
    Yield successive n-sized chunks from l.

    Note:
        Taken from https://stackoverflow.com/a/312464
    """
    if sys.version_info.major == 2:
        for i in xrange(0, len(l), n):
            yield l[i : i + n]
    else:
        # Assume Python 3
        for i in range(0, len(l), n):
            yield l[i : i + n]


def run_asyncio_commands(tasks, max_concurrent_tasks=0):
    """
    Run tasks asynchronously using asyncio and return results.

    If max_concurrent_tasks are set to 0, no limit is applied.
    """

    all_results = []

    if max_concurrent_tasks == 0:
        chunks = [tasks]
        num_chunks = len(chunks)
    else:
        chunks = make_chunks(l=tasks, n=max_concurrent_tasks)
        num_chunks = len(list(make_chunks(l=tasks, n=max_concurrent_tasks)))

    if asyncio.get_event_loop().is_closed():
        asyncio.set_event_loop(asyncio.new_event_loop())

    loop = asyncio.get_event_loop()
    
    chunk = 1
    for tasks_in_chunk in chunks:
        print(f"Beginning work on chunk {chunk}/{num_chunks}", flush=True)
        commands = asyncio.gather(*tasks_in_chunk)  # Unpack list using *
        results = loop.run_until_complete(commands)
        if loop.is_running():
            print('running')
        all_results += results
        print(
            "Completed work on chunk %s/%s" % (chunk, num_chunks), flush=True
        )
        chunk += 1

    loop.close()
    return all_results


def main():
    """Main program."""
    start = time.time()

    # Commands to be executed on Unix
    commands = [["nmap", "-sV", "-p-", "172.16.123.172"], ["hostname"]]

    tasks = []
    for command in commands:
        tasks.append(run_command(*command))

    results = run_asyncio_commands(
        tasks, max_concurrent_tasks=8
    )  # At most 20 parallel tasks
    print("Results:")
    pprint(results)

    end = time.time()
    rounded_end = "{0:.4f}".format(round(end - start, 4))
    print("Script ran in about %s seconds" % (rounded_end), flush=True)


if __name__ == "__main__":
    main()