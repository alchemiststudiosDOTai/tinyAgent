use std::sync::{Arc, Mutex};

use anyhow::{Result, anyhow};
use tokio::sync::{mpsc, oneshot};

pub fn event_stream<T, R>() -> (EventEmitter<T, R>, EventStream<T, R>) {
    let (sender, receiver) = mpsc::unbounded_channel();
    let (result_sender, result_receiver) = oneshot::channel();

    (
        EventEmitter {
            sender,
            result_sender: Arc::new(Mutex::new(Some(result_sender))),
        },
        EventStream {
            receiver,
            result_receiver,
        },
    )
}

#[derive(Clone)]
pub struct EventEmitter<T, R> {
    sender: mpsc::UnboundedSender<T>,
    result_sender: Arc<Mutex<Option<oneshot::Sender<Result<R>>>>>,
}

impl<T, R> EventEmitter<T, R> {
    pub fn push(&self, item: T) -> Result<()> {
        self.sender
            .send(item)
            .map_err(|_| anyhow!("event stream receiver dropped"))
    }

    pub fn finish(&self, result: R) -> Result<()> {
        let mut result_sender = self
            .result_sender
            .lock()
            .map_err(|_| anyhow!("event stream result sender poisoned"))?;
        if let Some(sender) = result_sender.take() {
            let _ = sender.send(Ok(result));
        }
        Ok(())
    }

    pub fn fail(&self, error: anyhow::Error) -> Result<()> {
        let mut result_sender = self
            .result_sender
            .lock()
            .map_err(|_| anyhow!("event stream result sender poisoned"))?;
        if let Some(sender) = result_sender.take() {
            let _ = sender.send(Err(error));
        }
        Ok(())
    }
}

pub struct EventStream<T, R> {
    receiver: mpsc::UnboundedReceiver<T>,
    result_receiver: oneshot::Receiver<Result<R>>,
}

impl<T, R> EventStream<T, R> {
    pub async fn next(&mut self) -> Option<T> {
        self.receiver.recv().await
    }

    pub async fn result(self) -> Result<R> {
        self.result_receiver
            .await
            .map_err(|_| anyhow!("event stream result channel dropped"))?
    }
}
