from threading import Timer, Lock
import threading

class ResettableTimer:
    """
    A timer that can be reset

    Methods
    -------
    callback_wrapper(generation)
        Wrapper for the callback function

    start()
        Start the timer

    reset()
        Reset the timer

    execute_and_reset()
        Execute the callback function and reset the timer

    stop()
        Stop the timer

    is_alive()
        Check if the timer is alive
    """
    def __init__(self, timeout, callback):
        """
        Initializes a new instance of the ResettableTimer class

        Attributes:
            timeout (int): The time to wait before executing the callback function
            callback (function): The function to execute when the timer expires            
            timer (Timer): The timer object            
            lock (Lock): The lock object
        """
        self.timeout = timeout
        self.callback = callback
        self._generation = 0
        self._stopped = True
        self.timer = Timer(
            self.timeout,
            self.callback_wrapper,
            args=(self._generation,),
        )
        self.lock = Lock()

    def _schedule_locked(self) -> None:
        self._generation += 1
        self._stopped = False
        self.timer = Timer(
            self.timeout,
            self.callback_wrapper,
            args=(self._generation,),
        )
        self.timer.start()

    def callback_wrapper(self, generation: int) -> None:
        """
        Executes the callback and rearms only if the callback did not reset or stop it.
        """
        with self.lock:
            if generation != self._generation:
                return

        self.callback()

        with self.lock:
            if generation == self._generation:
                self._schedule_locked()

    def start(self) -> None:
        """
        Start the timer if it is not already running
        """
        with self.lock:
            if self._stopped or not self.timer.is_alive():
                if self.timer.is_alive():
                    self.timer.cancel()
                self._schedule_locked()

    def reset(self) -> None:
        """
        Reset the timer if it is running
        """
        with self.lock:
            if self.timer.is_alive():
                self.timer.cancel()
            self._schedule_locked()


    def execute_and_reset(self) -> None:
        """
        Execute the callback function and reset the timer
        """
        with self.lock:
            if self.timer.is_alive():
                self.timer.cancel()
                self._generation += 1
                generation = self._generation
                threading.Thread(
                    target=self.callback_wrapper,
                    args=(generation,),
                ).start()

    def stop(self) -> None:
        """
        Stop the timer if it is running
        """
        with self.lock:
            self._stopped = True
            self._generation += 1
            if self.timer.is_alive():
                self.timer.cancel()

    def is_alive(self) -> bool:
        """
        Check if the timer is alive

        Returns:
            bool: True if the timer is alive, False otherwise
        """
        with self.lock:
            return not self._stopped and self.timer.is_alive()